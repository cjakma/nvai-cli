from __future__ import annotations

import os

DEFAULT_MAX_TOKENS = 1024
MIN_MAX_TOKENS = 1
MAX_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 180.0
MIN_TIMEOUT = 5.0
MAX_TIMEOUT = 600.0


def parse_max_tokens(value: str | None, *, default: int = DEFAULT_MAX_TOKENS) -> int:
    """Parse a user-provided max_tokens value with safe bounds."""
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"max_tokens must be an integer, got {value!r}") from exc
    if parsed < MIN_MAX_TOKENS:
        raise ValueError(f"max_tokens must be >= {MIN_MAX_TOKENS}")
    if parsed > MAX_MAX_TOKENS:
        raise ValueError(f"max_tokens must be <= {MAX_MAX_TOKENS}")
    return parsed


def default_max_tokens() -> int:
    """Return the default chat completion token cap.

    GLM 5.2 on NVIDIA's OpenAI-compatible endpoint can take more than the
    original 60 second read timeout before sending the first byte when asked for
    8192 output tokens. Keep the default responsive, while still allowing users
    to opt into larger generations via NVAI_MAX_TOKENS or --max-tokens.
    """
    return parse_max_tokens(os.environ.get("NVAI_MAX_TOKENS"))


def parse_timeout(value: str | None, *, default: float = DEFAULT_TIMEOUT) -> float:
    """Parse a request timeout in seconds with safe bounds."""
    if value is None or value.strip() == "":
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"timeout must be a number of seconds, got {value!r}") from exc
    if parsed < MIN_TIMEOUT:
        raise ValueError(f"timeout must be >= {MIN_TIMEOUT:g}s")
    if parsed > MAX_TIMEOUT:
        raise ValueError(f"timeout must be <= {MAX_TIMEOUT:g}s")
    return parsed


def default_timeout() -> float:
    """Return the default NVIDIA request timeout in seconds."""
    return parse_timeout(os.environ.get("NVAI_TIMEOUT"))
