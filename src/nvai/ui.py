from __future__ import annotations

import itertools
import sys
import threading
import time
from types import TracebackType
from typing import TextIO


class Status:
    """Small terminal status indicator for long-running CLI operations.

    On interactive TTYs it renders a spinner with elapsed time. On non-TTYs it
    emits start/done/fail lines so logs still show progress.
    """

    def __init__(self, message: str, *, stream: TextIO | None = None, interval: float = 0.12) -> None:
        self.message = message
        self.stream = stream or sys.stderr
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = 0.0
        self._is_tty = False

    def __enter__(self) -> Status:
        self._started = time.monotonic()
        self._is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        if self._is_tty:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            self.stream.write(f"[status] {self.message}...\n")
            self.stream.flush()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        elapsed = time.monotonic() - self._started
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval * 3)
        if self._is_tty:
            self.stream.write("\r" + " " * 100 + "\r")
        if exc_type is None:
            self.stream.write(f"[ok] {self.message} ({elapsed:.1f}s)\n")
        else:
            self.stream.write(f"[error] {self.message} failed after {elapsed:.1f}s\n")
        self.stream.flush()
        return None

    def _spin(self) -> None:
        frames = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
        while not self._stop.is_set():
            elapsed = time.monotonic() - self._started
            self.stream.write(f"\r{next(frames)} {self.message}... {elapsed:.1f}s")
            self.stream.flush()
            self._stop.wait(self.interval)
