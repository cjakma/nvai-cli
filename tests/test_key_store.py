from datetime import datetime, timedelta, timezone

from nvai.key_store import KeyStore, load_key_store, save_key_store
from nvai.models import ApiKeyRecord


def test_key_store_roundtrip_and_active(tmp_path):
    path = tmp_path / "keys.toml"
    rec = ApiKeyRecord(
        name="daily-glm-2026-07-08",
        model="nvidia/z-ai/glm-5.2",
        api_key="nvapi-test",
        expiredate=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )
    store = KeyStore(active_key=rec.name, keys=[rec])
    save_key_store(store, path)
    loaded = load_key_store(path)
    assert loaded.active_key == rec.name
    assert loaded.active().api_key == "nvapi-test"
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_is_expired_logic():
    now = datetime.now(timezone.utc)
    rec = ApiKeyRecord(name="k", model="m", api_key="secret", expiredate=now - timedelta(seconds=1))
    assert rec.is_expired(now)
    rec.expiredate = now + timedelta(seconds=60)
    assert not rec.is_expired(now)
