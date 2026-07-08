from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta


def local_tz():
    return datetime.now().astimezone().tzinfo


def default_expiredate(now: datetime | None = None) -> datetime:
    now = now or datetime.now().astimezone()
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0, 0), tzinfo=now.tzinfo)


def _parse_slash_date(raw: str) -> datetime | None:
    """Parse user-friendly slash dates.

    Supported forms:
    - YYYY/MM/DD
    - MM/DD/YYYY (default for ambiguous NVIDIA-style dates such as 01/08/2027)
    - DD/MM/YYYY when the first number is > 12
    """
    match = re.fullmatch(r"(\d{1,4})/(\d{1,2})/(\d{1,4})", raw)
    if not match:
        return None
    a, b, c = [int(part) for part in match.groups()]
    if a > 999:  # YYYY/MM/DD
        year, month, day = a, b, c
    elif c > 999:
        year = c
        if a > 12:  # DD/MM/YYYY, unambiguous
            day, month = a, b
        else:  # MM/DD/YYYY, including ambiguous inputs like 01/08/2027
            month, day = a, b
    else:
        return None
    d = date(year, month, day)
    return datetime.combine(d, time(0, 0), tzinfo=local_tz())


def parse_expiredate(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("expiredate is required")

    slash_dt = _parse_slash_date(raw)
    if slash_dt is not None:
        return slash_dt

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        d = date.fromisoformat(raw)
        return datetime.combine(d, time(0, 0), tzinfo=local_tz())

    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError(
                "expiredate must be one of: YYYY-MM-DD, YYYY-MM-DD HH:MM, "
                "YYYY-MM-DDTHH:MM:SS+09:00, YYYY/MM/DD, or MM/DD/YYYY"
            ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz())
    return dt


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone().isoformat(timespec="seconds")
