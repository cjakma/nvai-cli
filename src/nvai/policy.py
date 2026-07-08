from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


DEFAULT_DENY_SUBSTRINGS = (
    " rm -rf /",
    "rm -rf /",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "chmod -R 777 /",
    "chown -R ",
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
)

DEFAULT_DENY_FIRST_WORDS = {
    "rm",
    "mkfs",
    "fdisk",
    "parted",
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
}

DEFAULT_ALLOWED_FIRST_WORDS = {
    "python",
    "python3",
    "pytest",
    "uv",
    "git",
    "bash",
    "sh",
    "printf",
    "echo",
    "pwd",
    "true",
    "false",
    "ls",
    "find",
    "grep",
    "rg",
    "sed",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "date",
    "make",
    "npm",
    "node",
    "cargo",
    "go",
}


@dataclass(frozen=True, slots=True)
class CommandPolicy:
    mode: str = "ask"  # ask | strict | off
    allow: tuple[str, ...] = ()
    deny: tuple[str, ...] = DEFAULT_DENY_SUBSTRINGS
    allowed_first_words: frozenset[str] = frozenset(DEFAULT_ALLOWED_FIRST_WORDS)
    denied_first_words: frozenset[str] = frozenset(DEFAULT_DENY_FIRST_WORDS)

    @classmethod
    def default(cls) -> "CommandPolicy":
        return cls()

    @classmethod
    def from_config(cls, config_path: Path | None = None) -> "CommandPolicy":
        config_path = config_path or Path(os.environ.get("NVAI_POLICY_PATH", "~/.config/nvai/policy.toml")).expanduser()
        if not config_path.exists() or tomllib is None:
            return cls.default()
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        shell = data.get("shell", {}) if isinstance(data, dict) else {}
        mode = str(shell.get("mode", "ask")).strip().lower()
        if mode not in {"ask", "strict", "off"}:
            mode = "ask"
        allow = tuple(str(x) for x in shell.get("allow", []) if str(x).strip())
        deny = tuple(str(x) for x in shell.get("deny", DEFAULT_DENY_SUBSTRINGS) if str(x).strip())
        allowed_words = frozenset(str(x) for x in shell.get("allowed_first_words", DEFAULT_ALLOWED_FIRST_WORDS))
        denied_words = frozenset(str(x) for x in shell.get("denied_first_words", DEFAULT_DENY_FIRST_WORDS))
        return cls(mode=mode, allow=allow, deny=deny, allowed_first_words=allowed_words, denied_first_words=denied_words)

    def check(self, command: str) -> tuple[bool, str]:
        command = (command or "").strip()
        if not command:
            return False, "empty command"
        if self.mode == "off":
            return True, "policy disabled"
        lowered = f" {command.lower()} "
        for denied in self.deny:
            if denied.lower() in lowered:
                return False, f"command denied by policy substring: {denied}"
        try:
            first_word = shlex.split(command, posix=True)[0]
        except ValueError as exc:
            return False, f"command parse failed: {exc}"
        base = Path(first_word).name
        if base in self.denied_first_words:
            return False, f"command denied by first word: {base}"
        if self.allow and not any(command.startswith(prefix) for prefix in self.allow):
            return False, "command is not in configured allow prefixes"
        if self.mode == "strict" and base not in self.allowed_first_words:
            return False, f"command first word is not allowed in strict mode: {base}"
        return True, "allowed"


def describe_policy(policy: CommandPolicy) -> str:
    return (
        f"shell policy mode={policy.mode}, "
        f"allow_prefixes={len(policy.allow)}, deny_rules={len(policy.deny)}, "
        f"strict_allowed_words={len(policy.allowed_first_words)}"
    )
