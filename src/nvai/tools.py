from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ACTION_BLOCK_RE = re.compile(r"```(?:nvai-actions|nvai_action|json)\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(slots=True)
class ToolResult:
    ok: bool
    action: str
    message: str
    content: str = ""


def parse_action_blocks(text: str) -> list[dict[str, Any]]:
    """Parse model-proposed nvai action blocks from fenced JSON.

    Accepted forms:
    ```nvai-actions
    [{"action":"read_file","path":"README.md"}]
    ```

    ```nvai_action
    {"action":"shell","command":"pytest -q"}
    ```
    """
    actions: list[dict[str, Any]] = []
    for match in ACTION_BLOCK_RE.finditer(text or ""):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            actions.extend(item for item in parsed if isinstance(item, dict) and item.get("action"))
    return actions


def _safe_path(path: str, *, cwd: Path | None = None) -> Path:
    cwd = (cwd or Path.cwd()).resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate.resolve()


def read_file_tool(path: str, *, max_bytes: int = 12000, cwd: Path | None = None) -> ToolResult:
    p = _safe_path(path, cwd=cwd)
    if not p.exists():
        return ToolResult(False, "read_file", f"file not found: {p}")
    if not p.is_file():
        return ToolResult(False, "read_file", f"not a file: {p}")
    data = p.read_bytes()[:max_bytes]
    text = data.decode("utf-8", errors="replace")
    truncated = "\n...[truncated]" if p.stat().st_size > max_bytes else ""
    return ToolResult(True, "read_file", f"read {p}", text + truncated)


def patch_preview(path: str, old: str, new: str, *, cwd: Path | None = None) -> tuple[bool, str, Path | None]:
    p = _safe_path(path, cwd=cwd)
    if not p.exists() or not p.is_file():
        return False, f"file not found: {p}", p
    text = p.read_text(encoding="utf-8", errors="replace")
    count = text.count(old)
    if count == 0:
        return False, f"old text not found in {p}", p
    if count > 1:
        return False, f"old text is not unique in {p}: {count} matches", p
    updated = text.replace(old, new, 1)
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(p),
            tofile=str(p),
        )
    )
    return True, diff, p


def patch_file_tool(path: str, old: str, new: str, *, cwd: Path | None = None) -> ToolResult:
    ok, preview, p = patch_preview(path, old, new, cwd=cwd)
    if not ok:
        return ToolResult(False, "patch_file", preview)
    assert p is not None
    text = p.read_text(encoding="utf-8", errors="replace")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return ToolResult(True, "patch_file", f"patched {p}", preview)


def shell_preview(command: str) -> str:
    return f"Command to execute:\n\n    {command}\n"


def shell_tool(command: str, *, cwd: Path | None = None, timeout: int = 120) -> ToolResult:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd or Path.cwd()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = proc.stdout[-20000:]
    ok = proc.returncode == 0
    return ToolResult(ok, "shell", f"exit_code={proc.returncode}", output)


def approve(prompt: str, *, auto_approve: bool = False) -> bool:
    if auto_approve:
        print("[approval] auto-approved")
        return True
    if not os.isatty(0):
        print("[approval] denied: non-interactive terminal. Re-run with --yes to approve proposed actions.")
        return False
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def run_action(action: dict[str, Any], *, auto_approve: bool = False, cwd: Path | None = None) -> ToolResult:
    kind = str(action.get("action", "")).strip()
    if kind == "read_file":
        return read_file_tool(str(action.get("path", "")), max_bytes=int(action.get("max_bytes", 12000)), cwd=cwd)
    if kind == "patch_file":
        path = str(action.get("path", ""))
        old = str(action.get("old", ""))
        new = str(action.get("new", ""))
        ok, preview, _ = patch_preview(path, old, new, cwd=cwd)
        print("\n[diff preview]\n" + preview)
        if not ok:
            return ToolResult(False, "patch_file", preview)
        if not approve("Apply this patch?", auto_approve=auto_approve):
            return ToolResult(False, "patch_file", "user denied patch")
        return patch_file_tool(path, old, new, cwd=cwd)
    if kind == "shell":
        command = str(action.get("command", ""))
        print("\n[shell preview]\n" + shell_preview(command))
        if not approve("Run this command?", auto_approve=auto_approve):
            return ToolResult(False, "shell", "user denied shell command")
        return shell_tool(command, cwd=cwd, timeout=int(action.get("timeout", 120)))
    return ToolResult(False, kind or "unknown", f"unknown action: {kind}")


def format_tool_results(results: list[ToolResult]) -> str:
    parts = []
    for idx, result in enumerate(results, 1):
        status = "ok" if result.ok else "error"
        block = f"### Tool result {idx}: {result.action} ({status})\n{result.message}"
        if result.content:
            block += f"\n\n```text\n{result.content}\n```"
        parts.append(block)
    return "\n\n".join(parts)
