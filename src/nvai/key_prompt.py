from __future__ import annotations

import getpass
import re
import sys
import termios
import tty
from datetime import datetime

from .datetime_utils import default_expiredate, format_dt, parse_expiredate
from .models import DEFAULT_BASE_URL, DEFAULT_MODEL, ApiKeyRecord


def suggest_daily_name(now: datetime | None = None, model: str = DEFAULT_MODEL) -> str:
    now = now or datetime.now().astimezone()
    short_model = model.split("/")[-1].replace(".", "-")
    return f"daily-{short_model}-{now.date().isoformat()}"


def normalize_base_url(value: str) -> str:
    """Normalize common pasted URL variants into a bare HTTPS base URL."""
    raw = value.strip()
    slack = re.fullmatch(r"<([^|>]+)(?:\|[^>]+)?>", raw)
    if slack:
        raw = slack.group(1).strip()
    paren = re.search(r"\((https?://[^)\s]+)\)", raw)
    if paren:
        raw = paren.group(1).strip()
    elif " " in raw:
        raw = raw.split()[0].strip()
    raw = raw.strip("<>")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "https://" + raw
    return raw.rstrip("/")


def masked_input(prompt: str) -> str:
    """Read a secret while echoing '*' for each typed character on real TTYs."""
    if not sys.stdin.isatty():
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return sys.stdin.readline().rstrip("\n")
    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars: list[str] = []
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in {"\r", "\n"}:
                sys.stdout.write("\n")
                return "".join(chars)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in {"\x7f", "\b"}:
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if ch == "\x04":
                raise EOFError
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _prompt(label: str, default: str | None = None, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    prompt = f"{label}{suffix}: "
    if secret:
        try:
            value = masked_input(prompt)
        except (termios.error, OSError):
            value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    value = value.strip()
    if not value and default is not None:
        return default
    return value


def prompt_expiredate(default: str) -> datetime:
    while True:
        expire_raw = _prompt("Expire date", default)
        try:
            return parse_expiredate(expire_raw)
        except ValueError as exc:
            print(f"Invalid expire date: {exc}")
            print("Examples: 2027-01-08, 2027-01-08 00:00, 2027/01/08, 01/08/2027")


def prompt_new_key(
    *,
    default_name: str | None = None,
    default_model: str = DEFAULT_MODEL,
    default_base_url: str = DEFAULT_BASE_URL,
) -> ApiKeyRecord:
    now = datetime.now().astimezone()
    name = _prompt("Name", default_name or suggest_daily_name(now, default_model))
    model = _prompt("Model", default_model)
    base_url = normalize_base_url(_prompt("Base URL", default_base_url))
    api_key = _prompt("API Key", secret=True)
    expire_default = format_dt(default_expiredate(now))
    return ApiKeyRecord(
        name=name,
        model=model,
        api_key=api_key,
        expiredate=prompt_expiredate(expire_default),
        base_url=base_url,
        created_at=now,
    )
