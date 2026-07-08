from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .key_store import default_key_store_path, load_key_store


def _yes_no(value: bool) -> str:
    return "OK" if value else "missing"


def run_doctor() -> int:
    """Print install/runtime diagnostics without making network calls."""
    executable = shutil.which("nvai")
    key_path = default_key_store_path()
    store = load_key_store(key_path)
    active = store.active()

    print("nvai doctor")
    print(f"Executable: {executable or 'not found in PATH'}")
    print(f"Python: {sys.executable}")
    print(f"Python exists: {_yes_no(Path(sys.executable).exists())}")
    print(f"Current directory: {Path.cwd()}")
    print(f"PATH contains ~/.local/bin: {_yes_no(str(Path.home() / '.local/bin') in os.environ.get('PATH', '').split(':'))}")
    print(f"Key store: {key_path}")
    print(f"Key store exists: {_yes_no(key_path.exists())}")

    if active is None:
        print("Active key: not configured")
    else:
        status = "expired" if active.is_expired() else "valid"
        print(f"Active key: {active.name}")
        print(f"Model: {active.model}")
        print(f"Base URL: {active.base_url}")
        print(f"API Key: {active.masked_key}")
        print(f"Expire date: {active.expiredate.astimezone().isoformat(timespec='seconds')}")
        print(f"Key status: {status}")

    if executable is None:
        return 1
    return 0
