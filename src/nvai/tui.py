from __future__ import annotations

import curses
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True)
class TuiState:
    title: str = "nvai full-screen TUI"
    transcript: deque[str] = field(default_factory=lambda: deque(maxlen=500))
    input_text: str = ""
    status: str = "F2 send · F10 quit · Enter inserts newline"

    def add(self, role: str, text: str) -> None:
        self.transcript.append(f"{role}: {text}")


def render_lines(state: TuiState, *, width: int, height: int) -> list[str]:
    """Pure renderer used by curses and tests."""
    width = max(width, 20)
    height = max(height, 5)
    lines = [state.title[:width].ljust(width), "─" * width]
    body_height = height - 5
    body = list(state.transcript)[-body_height:]
    lines.extend(line[:width].ljust(width) for line in body)
    while len(lines) < height - 3:
        lines.append(" " * width)
    lines.append("─" * width)
    prompt = ("> " + state.input_text.replace("\n", " ⏎ "))[:width]
    lines.append(prompt.ljust(width))
    lines.append(state.status[:width].ljust(width))
    return lines[:height]


def run_curses_tui(send_message: Callable[[str], str] | None = None) -> int:
    """Run a minimal full-screen curses chat UI.

    The callable receives a user message and returns assistant text. This keeps the
    curses layer small and lets tests exercise rendering without a terminal.
    """
    send_message = send_message or (lambda message: "TUI transport is ready. Use `nvai ask` for model-backed runs in this build.")
    state = TuiState()
    state.add("system", "Full-screen mode started. Type a message, F2 to send, F10 to quit.")

    def _main(stdscr) -> int:
        curses.curs_set(1)
        stdscr.keypad(True)
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            for row, line in enumerate(render_lines(state, width=width, height=height)):
                try:
                    stdscr.addstr(row, 0, line[: max(0, width - 1)])
                except curses.error:
                    pass
            stdscr.refresh()
            key = stdscr.getch()
            if key in {curses.KEY_F10, 27}:  # F10 or Esc
                return 0
            if key == curses.KEY_F2:
                message = state.input_text.strip()
                if not message:
                    continue
                state.add("user", message)
                state.input_text = ""
                state.status = "waiting for model..."
                stdscr.refresh()
                try:
                    answer = send_message(message)
                    state.add("assistant", answer)
                    state.status = "F2 send · F10 quit · Enter inserts newline"
                except Exception as exc:  # pragma: no cover - defensive UI boundary
                    state.add("error", str(exc))
                    state.status = "error; continue or F10 quit"
                continue
            if key in {curses.KEY_BACKSPACE, 127, 8}:
                state.input_text = state.input_text[:-1]
                continue
            if key in {10, 13}:
                state.input_text += "\n"
                continue
            if 0 <= key <= 255:
                char = chr(key)
                if char.isprintable():
                    state.input_text += char
        return 0

    return curses.wrapper(_main)
