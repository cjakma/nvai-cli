from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .nvidia_client import NvidiaClient
from .tools import format_tool_results, parse_action_blocks, run_action
from .ui import Status

ACTION_INSTRUCTIONS = """

Tool protocol:
When you need local project evidence or want to modify/run something, propose actions in a fenced JSON block.
Use only these actions:
```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```
Rules:
- Prefer read_file before patching unknown files.
- patch_file must use exact, unique old text.
- shell and patch_file require user approval and will show preview first.
- Never claim an action ran until a tool result is returned.
"""


def stream_or_chat(client: NvidiaClient, messages: list[dict[str, Any]], *, stream: bool, model: str) -> str:
    if stream:
        print(f"[stream] Waiting for NVIDIA model response ({model})...", file=sys.stderr)
        chunks: list[str] = []
        for chunk in client.chat_stream(messages):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        print()
        return "".join(chunks)
    with Status(f"Waiting for NVIDIA model response ({model})"):
        return client.chat(messages)


def run_agent_turn(
    client: NvidiaClient,
    history: list[dict[str, Any]],
    *,
    stream: bool = True,
    auto_approve: bool = False,
    max_rounds: int = 3,
    cwd: Path | None = None,
) -> str:
    """Run a small Codex-like action loop.

    The model answers, optionally proposes action blocks, nvai executes approved
    actions, feeds tool results back, and lets the model continue. This is bounded
    by max_rounds to avoid infinite loops.
    """
    last_answer = ""
    for round_index in range(max_rounds):
        answer = stream_or_chat(client, history, stream=stream, model=client.key.model)
        last_answer = answer
        if not stream:
            print(answer)
        history.append({"role": "assistant", "content": answer})
        actions = parse_action_blocks(answer)
        if not actions:
            return answer
        print(f"[actions] {len(actions)} proposed action(s)")
        results = [run_action(action, auto_approve=auto_approve, cwd=cwd) for action in actions]
        result_text = format_tool_results(results)
        print("\n[tool results]\n" + result_text)
        history.append({"role": "user", "content": "Tool results:\n" + result_text + "\n\nContinue from these results."})
        if round_index == max_rounds - 1:
            print("[actions] max action rounds reached; stopping.")
    return last_answer
