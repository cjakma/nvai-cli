from __future__ import annotations

import os
from datetime import datetime

from .key_prompt import prompt_new_key, suggest_daily_name
from .key_store import KeyStore, load_key_store, save_key_store
from .models import DEFAULT_BASE_URL, DEFAULT_MODEL, ApiKeyRecord
from .nvidia_client import NvidiaApiError, NvidiaClient
from .ui import Status


def validate_or_raise(record: ApiKeyRecord) -> None:
    if os.environ.get("NVAI_SKIP_VALIDATE") == "1":
        return
    client = NvidiaClient(record, timeout=30.0)
    ok, msg = client.validate_key(require_model=False)
    if not ok:
        raise NvidiaApiError(msg)


def ensure_valid_api_key(*, force_refresh: bool = False) -> ApiKeyRecord:
    store = load_key_store()
    now = datetime.now().astimezone()
    active = store.active()

    if active is None:
        print("[auth] No NVIDIA API key is configured.")
        return _collect_validate_save(store, default_model=DEFAULT_MODEL, default_base_url=DEFAULT_BASE_URL)

    if force_refresh or active.is_expired(now):
        if force_refresh:
            print("[auth] Refreshing NVIDIA API key.")
        else:
            print("[auth] Stored NVIDIA API key has expired.")
            print(f"- name: {active.name}")
            print(f"- expired at: {active.expiredate.astimezone().isoformat(timespec='seconds')}")
        return _collect_validate_save(
            store,
            default_name=suggest_daily_name(now, active.model),
            default_model=active.model,
            default_base_url=active.base_url,
        )

    active.last_used_at = now
    save_key_store(store)
    return active


def _collect_validate_save(
    store: KeyStore,
    *,
    default_name: str | None = None,
    default_model: str = DEFAULT_MODEL,
    default_base_url: str = DEFAULT_BASE_URL,
) -> ApiKeyRecord:
    record = prompt_new_key(default_name=default_name, default_model=default_model, default_base_url=default_base_url)
    print("[auth] validating key with NVIDIA API...")
    with Status("Validating NVIDIA API key"):
        validate_or_raise(record)
    print("[auth] OK.")
    store.upsert(record)
    store.active_key = record.name
    save_key_store(store)
    return record
