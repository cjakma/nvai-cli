from nvai.tools import parse_action_blocks, patch_preview, patch_file_tool, read_file_tool, run_action, shell_tool


def test_parse_action_blocks_single_and_list():
    text = '''hello
```nvai-actions
[{"action":"read_file","path":"README.md"}, {"action":"shell","command":"pytest -q"}]
```
```nvai_action
{"action":"read_file","path":"pyproject.toml"}
```
'''
    actions = parse_action_blocks(text)
    assert [a["action"] for a in actions] == ["read_file", "shell", "read_file"]


def test_read_file_tool(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    result = read_file_tool("a.txt", cwd=tmp_path)
    assert result.ok is True
    assert result.content == "hello"


def test_patch_preview_and_apply(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world\n", encoding="utf-8")
    ok, diff, _ = patch_preview("a.txt", "world", "nvai", cwd=tmp_path)
    assert ok is True
    assert "-hello world" in diff
    assert "+hello nvai" in diff
    result = patch_file_tool("a.txt", "world", "nvai", cwd=tmp_path)
    assert result.ok is True
    assert p.read_text(encoding="utf-8") == "hello nvai\n"


def test_shell_tool(tmp_path):
    result = shell_tool("printf ok", cwd=tmp_path)
    assert result.ok is True
    assert result.content == "ok"


def test_run_action_denies_shell_without_tty(tmp_path, capsys):
    result = run_action({"action": "shell", "command": "printf nope"}, cwd=tmp_path)
    captured = capsys.readouterr()
    assert result.ok is False
    assert "denied" in result.message
    assert "shell preview" in captured.out
