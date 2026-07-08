from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .agent import ACTION_INSTRUCTIONS, run_agent_turn
from .auth_flow import ensure_valid_api_key
from .context import collect_project_context
from .doctor import run_doctor
from .key_store import load_key_store, save_key_store
from .nvidia_client import NvidiaApiError, NvidiaClient
from .policy import CommandPolicy, describe_policy
from .tui import run_curses_tui
from .ui import Status

SYSTEM_PROMPT = """You are nvai, a coding assistant running in a Linux CLI.
Be concise, practical, and safe. If code changes are needed, use the nvai tool protocol to read files, propose patches, or run commands.
Never claim a file was changed or a command was run unless tool results show it happened.
""" + ACTION_INSTRUCTIONS

REPL_HELP = """Commands:
  /help      Show this help
  /context   Add current project context to the conversation
  /exit      Quit nvai
  /quit      Quit nvai

Agent workflow:
  nvai can read files, preview patches, and propose shell commands through action blocks.
  patch_file and shell actions show a preview and ask for approval before running.

Shortcuts:
  Ctrl+C     Quit nvai and return to the terminal
  Ctrl+D     Quit nvai and return to the terminal
"""


def _cmd_auth(args: argparse.Namespace) -> int:
    if args.auth_command == "status":
        store = load_key_store()
        active = store.active()
        if active is None:
            print("No active key configured.")
            return 1
        status = "expired" if active.is_expired() else "valid"
        print("Active NVIDIA API key")
        print(f"Name: {active.name}")
        print(f"Model: {active.model}")
        print(f"Base URL: {active.base_url}")
        print(f"API Key: {active.masked_key}")
        print(f"Expire date: {active.expiredate.astimezone().isoformat(timespec='seconds')}")
        print(f"Status: {status}")
        return 0
    if args.auth_command in {"add", "refresh"}:
        ensure_valid_api_key(force_refresh=args.auth_command == "refresh")
        return 0
    if args.auth_command == "list":
        store = load_key_store()
        if not store.keys:
            print("No keys configured.")
            return 0
        for rec in store.keys:
            prefix = "*" if rec.name == store.active_key else " "
            status = "expired" if rec.is_expired() else "valid"
            expires = rec.expiredate.astimezone().isoformat(timespec="seconds")
            print(f"{prefix} {rec.name}  {rec.model}  {status}  expires={expires}")
        return 0
    if args.auth_command == "use":
        store = load_key_store()
        rec = store.get(args.name)
        if rec is None:
            print(f"Key not found: {args.name}", file=sys.stderr)
            return 1
        if rec.is_expired() and not args.allow_expired:
            print("Selected key is expired. Re-run with --allow-expired to force.", file=sys.stderr)
            return 1
        store.active_key = rec.name
        rec.last_used_at = datetime.now().astimezone()
        save_key_store(store)
        print(f"Active key set to {rec.name}")
        return 0
    print("Missing auth subcommand", file=sys.stderr)
    return 2


def _messages(prompt: str, include_context: bool = True) -> list[dict]:
    content = prompt
    if include_context:
        content = f"Project context:\n{collect_project_context()}\n\nUser request:\n{prompt}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}]


def _ask(
    prompt: str,
    *,
    include_context: bool = True,
    stream: bool = True,
    auto_approve: bool = False,
    policy_mode: str | None = None,
    batch_patches: bool = True,
    detect_stream_actions: bool = True,
) -> int:
    key = ensure_valid_api_key()
    client = NvidiaClient(key)
    policy = CommandPolicy.from_config()
    if policy_mode:
        policy = CommandPolicy(
            mode=policy_mode,
            allow=policy.allow,
            deny=policy.deny,
            allowed_first_words=policy.allowed_first_words,
            denied_first_words=policy.denied_first_words,
        )
    with Status("Collecting project context" if include_context else "Preparing prompt"):
        messages = _messages(prompt, include_context=include_context)
    print(f"[policy] {describe_policy(policy)}", file=sys.stderr)
    run_agent_turn(
        client,
        messages,
        stream=stream,
        auto_approve=auto_approve,
        policy=policy,
        batch_patches=batch_patches,
        detect_stream_actions=detect_stream_actions,
    )
    return 0


def _cmd_models(args: argparse.Namespace) -> int:
    key = ensure_valid_api_key()
    client = NvidiaClient(key)
    with Status("Fetching NVIDIA model list"):
        models = client.list_models()
    for model in models:
        marker = "*" if model == key.model else " "
        print(f"{marker} {model}")
    return 0


def _repl() -> int:
    key = ensure_valid_api_key()
    client = NvidiaClient(key)
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("nvai interactive mode. Type /help for commands. Ctrl+C exits.")
    while True:
        try:
            prompt = input("nvai> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not prompt:
            continue
        if prompt in {"/exit", "/quit"}:
            print("bye")
            return 0
        if prompt == "/help":
            print(REPL_HELP)
            continue
        if prompt == "/context":
            with Status("Collecting project context"):
                context = collect_project_context()
            history.append({"role": "user", "content": "Project context:\n" + context})
            print("[context] added")
            continue
        history.append({"role": "user", "content": prompt})
        run_agent_turn(client, history, stream=True, auto_approve=False)


def _cmd_tui(args: argparse.Namespace) -> int:
    key = ensure_valid_api_key()
    client = NvidiaClient(key)
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def send_message(message: str) -> str:
        history.append({"role": "user", "content": message})
        answer = client.chat(history)
        history.append({"role": "assistant", "content": answer})
        return answer

    return run_curses_tui(send_message)


KNOWN_COMMANDS = {"auth", "models", "ask", "doctor", "tui"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nvai", description="NVIDIA AI coding CLI")
    sub = parser.add_subparsers(dest="command")

    auth = sub.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_sub.add_parser("status")
    auth_sub.add_parser("add")
    auth_sub.add_parser("refresh")
    auth_sub.add_parser("list")
    use = auth_sub.add_parser("use")
    use.add_argument("name")
    use.add_argument("--allow-expired", action="store_true")

    sub.add_parser("models")
    sub.add_parser("doctor")
    sub.add_parser("tui", help="open a minimal full-screen curses UI")
    ask = sub.add_parser("ask")
    ask.add_argument("prompt")
    ask.add_argument("--no-context", action="store_true")
    ask.add_argument("--no-stream", action="store_true", help="disable streaming output")
    ask.add_argument("--yes", action="store_true", help="auto-approve proposed patch/shell actions")
    ask.add_argument("--policy", choices=["ask", "strict", "off"], default=None, help="override shell command policy mode")
    ask.add_argument("--no-batch-patches", action="store_true", help="approve patch_file actions one by one")
    ask.add_argument("--no-stream-detect", action="store_true", help="disable action-block detection while streaming")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in KNOWN_COMMANDS and not argv[0].startswith("-"):
        return _ask(" ".join(argv))
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "auth":
            return _cmd_auth(args)
        if args.command == "models":
            return _cmd_models(args)
        if args.command == "doctor":
            return run_doctor()
        if args.command == "tui":
            return _cmd_tui(args)
        if args.command == "ask":
            return _ask(
                args.prompt,
                include_context=not args.no_context,
                stream=not args.no_stream,
                auto_approve=args.yes,
                policy_mode=args.policy,
                batch_patches=not args.no_batch_patches,
                detect_stream_actions=not args.no_stream_detect,
            )
        return _repl()
    except NvidiaApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
