from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .datetime_utils import format_dt, parse_expiredate
from .models import DEFAULT_BASE_URL, ApiKeyRecord


def default_key_store_path() -> Path:
    return Path(os.environ.get("NVAI_KEY_STORE", "~/.config/nvai/keys.toml")).expanduser()


@dataclass(slots=True)
class KeyStore:
    active_key: str | None = None
    keys: list[ApiKeyRecord] = field(default_factory=list)

    def get(self, name: str) -> ApiKeyRecord | None:
        return next((k for k in self.keys if k.name == name), None)

    def active(self) -> ApiKeyRecord | None:
        if not self.active_key:
            return None
        return self.get(self.active_key)

    def upsert(self, record: ApiKeyRecord) -> None:
        for idx, existing in enumerate(self.keys):
            if existing.name == record.name:
                self.keys[idx] = record
                return
        self.keys.append(record)


def _parse_dt(value: str | None) -> datetime | None:
    return parse_expiredate(value) if value else None


def load_key_store(path: Path | None = None) -> KeyStore:
    path = path or default_key_store_path()
    if not path.exists():
        return KeyStore()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    store = KeyStore(active_key=data.get("active_key"))
    for item in data.get("keys", []):
        store.keys.append(
            ApiKeyRecord(
                name=item["name"],
                model=item["model"],
                api_key=item["api_key"],
                expiredate=parse_expiredate(item["expiredate"]),
                base_url=item.get("base_url", DEFAULT_BASE_URL),
                created_at=_parse_dt(item.get("created_at")) or datetime.now().astimezone(),
                last_used_at=_parse_dt(item.get("last_used_at")),
            )
        )
    return store


def _toml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dump_key_store(store: KeyStore) -> str:
    lines: list[str] = []
    if store.active_key:
        lines.append(f"active_key = {_toml_quote(store.active_key)}")
        lines.append("")
    for rec in store.keys:
        lines.append("[[keys]]")
        lines.append(f"name = {_toml_quote(rec.name)}")
        lines.append(f"model = {_toml_quote(rec.model)}")
        lines.append(f"api_key = {_toml_quote(rec.api_key)}")
        lines.append(f"expiredate = {_toml_quote(format_dt(rec.expiredate))}")
        lines.append(f"base_url = {_toml_quote(rec.base_url)}")
        lines.append(f"created_at = {_toml_quote(format_dt(rec.created_at))}")
        if rec.last_used_at:
            lines.append(f"last_used_at = {_toml_quote(format_dt(rec.last_used_at))}")
        lines.append("")
    return "\n".join(lines)


def save_key_store(store: KeyStore, path: Path | None = None) -> None:
    path = path or default_key_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dump_key_store(store), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    os.chmod(path, 0o600)
