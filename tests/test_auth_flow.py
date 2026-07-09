from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from nvai.auth_flow import ensure_valid_api_key
from nvai.key_store import KeyStore, load_key_store, save_key_store
from nvai.models import ApiKeyRecord


def _record(*, now: datetime, last_validated_at: datetime | None = None) -> ApiKeyRecord:
    return ApiKeyRecord(
        name="daily",
        model="z-ai/glm-5.2",
        api_key="nvapi-test",
        expiredate=now + timedelta(days=30),
        last_validated_at=last_validated_at,
    )


def test_key_store_roundtrips_last_validated_at(tmp_path):
    now = datetime(2026, 7, 9, 9, 0, tzinfo=timezone.utc)
    path = tmp_path / "keys.toml"
    rec = _record(now=now, last_validated_at=now)
    save_key_store(KeyStore(active_key=rec.name, keys=[rec]), path)

    loaded = load_key_store(path)

    assert loaded.active().last_validated_at == now


def test_ensure_valid_api_key_validates_once_per_day(tmp_path, monkeypatch):
    now = datetime(2026, 7, 9, 9, 0, tzinfo=timezone.utc)
    path = tmp_path / "keys.toml"
    rec = _record(now=now, last_validated_at=None)
    save_key_store(KeyStore(active_key=rec.name, keys=[rec]), path)
    monkeypatch.setenv("NVAI_KEY_STORE", str(path))

    with patch("nvai.auth_flow.validate_or_raise") as validate:
        first = ensure_valid_api_key(now=now)
        second = ensure_valid_api_key(now=now + timedelta(hours=1))

    assert first.api_key == "nvapi-test"
    assert second.api_key == "nvapi-test"
    assert validate.call_count == 1
    assert load_key_store(path).active().last_validated_at.date() == now.date()


def test_ensure_valid_api_key_revalidates_on_next_day(tmp_path, monkeypatch):
    now = datetime(2026, 7, 9, 9, 0, tzinfo=timezone.utc)
    path = tmp_path / "keys.toml"
    rec = _record(now=now, last_validated_at=now)
    save_key_store(KeyStore(active_key=rec.name, keys=[rec]), path)
    monkeypatch.setenv("NVAI_KEY_STORE", str(path))

    with patch("nvai.auth_flow.validate_or_raise") as validate:
        ensure_valid_api_key(now=now + timedelta(days=1))

    assert validate.call_count == 1
