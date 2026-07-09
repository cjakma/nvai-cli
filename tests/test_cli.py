from datetime import datetime, timedelta
from unittest.mock import patch

from nvai.cli import _repl, build_parser, main
from nvai.models import ApiKeyRecord
from nvai.nvidia_client import NvidiaApiError


def test_one_shot_prompt_routes_before_argparse():
    with patch("nvai.cli._ask", return_value=0) as ask:
        assert main(["hello", "world"]) == 0
    ask.assert_called_once_with("hello world")


def test_auth_use_parses():
    args = build_parser().parse_args(["auth", "use", "mykey", "--allow-expired"])
    assert args.command == "auth"
    assert args.auth_command == "use"
    assert args.name == "mykey"
    assert args.allow_expired is True


def test_doctor_parses():
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"


def test_ask_tool_flags_parse():
    args = build_parser().parse_args([
        "ask",
        "hello",
        "--no-context",
        "--no-stream",
        "--yes",
        "--policy",
        "strict",
        "--no-batch-patches",
        "--no-stream-detect",
    ])
    assert args.command == "ask"
    assert args.no_context is True
    assert args.no_stream is True
    assert args.yes is True
    assert args.policy == "strict"
    assert args.no_batch_patches is True
    assert args.no_stream_detect is True


def test_ask_shows_progress_messages(capsys):
    key = ApiKeyRecord(
        name="k",
        model="z-ai/glm-5.2",
        api_key="secret",
        expiredate=datetime.now().astimezone() + timedelta(days=1),
    )
    with patch("nvai.cli.ensure_valid_api_key", return_value=key), patch("nvai.cli.collect_project_context", return_value="ctx"):
        with patch("nvai.cli.NvidiaClient") as client_cls:
            client_cls.return_value.key = key
            client_cls.return_value.chat_stream.return_value = iter(["answer"])
            assert main(["ask", "hello"]) == 0
    captured = capsys.readouterr()
    assert "answer" in captured.out
    assert "Collecting project context" in captured.err
    assert "Waiting for NVIDIA model response (z-ai/glm-5.2)" in captured.err


def test_repl_help_and_exit(capsys):
    key = ApiKeyRecord(
        name="k",
        model="z-ai/glm-5.2",
        api_key="secret",
        expiredate=datetime.now().astimezone() + timedelta(days=1),
    )
    with patch("nvai.cli.ensure_valid_api_key", return_value=key), patch("nvai.cli.NvidiaClient"):
        with patch("builtins.input", side_effect=["/help", "/exit"]):
            assert _repl() == 0
    captured = capsys.readouterr()
    assert "Type /help for commands" in captured.out
    assert "/context" in captured.out
    assert "Ctrl+C" in captured.out
    assert "bye" in captured.out


def test_repl_ctrl_c_prints_bye(capsys):
    key = ApiKeyRecord(
        name="k",
        model="z-ai/glm-5.2",
        api_key="secret",
        expiredate=datetime.now().astimezone() + timedelta(days=1),
    )
    with patch("nvai.cli.ensure_valid_api_key", return_value=key), patch("nvai.cli.NvidiaClient"):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            assert _repl() == 0
    captured = capsys.readouterr()
    assert "bye" in captured.out


def test_ask_max_tokens_flag_parse():
    args = build_parser().parse_args(["ask", "hello", "--max-tokens", "128", "--timeout", "30"])
    assert args.max_tokens == 128
    assert args.timeout == 30.0


def test_repl_handles_nvidia_api_error_without_traceback(capsys):
    key = ApiKeyRecord(
        name="k",
        model="z-ai/glm-5.2",
        api_key="secret",
        expiredate=datetime.now().astimezone() + timedelta(days=1),
    )
    with patch("nvai.cli.ensure_valid_api_key", return_value=key), patch("nvai.cli.NvidiaClient"):
        with patch("builtins.input", side_effect=["hello", "/exit"]):
            with patch("nvai.cli.run_agent_turn", side_effect=NvidiaApiError("timed out")):
                assert _repl() == 0
    captured = capsys.readouterr()
    assert "error: timed out" in captured.err
    assert "Traceback" not in captured.err
    assert "bye" in captured.out
