from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from nvai.doctor import run_doctor
from nvai.key_store import KeyStore, save_key_store
from nvai.models import ApiKeyRecord


def test_doctor_reports_active_key(tmp_path, monkeypatch, capsys):
    key_path = tmp_path / "keys.toml"
    rec = ApiKeyRecord(
        name="doctor-key",
        model="z-ai/glm-5.2",
        api_key="nvapi-secret-value",
        expiredate=datetime.now(timezone.utc) + timedelta(days=1),
    )
    save_key_store(KeyStore(active_key=rec.name, keys=[rec]), key_path)
    monkeypatch.setenv("NVAI_KEY_STORE", str(key_path))
    monkeypatch.setenv("PATH", f"{Path.home() / '.local/bin'}:/usr/bin")

    with patch("shutil.which", return_value=str(Path.home() / ".local/bin/nvai")):
        assert run_doctor() == 0
    output = capsys.readouterr().out
    assert "nvai doctor" in output
    assert "Executable:" in output
    assert "Active key: doctor-key" in output
    assert "API Key: nvapi-****alue" in output
    assert "Key status: valid" in output


def test_doctor_returns_nonzero_when_executable_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NVAI_KEY_STORE", str(tmp_path / "missing.toml"))
    with patch("shutil.which", return_value=None):
        assert run_doctor() == 1
    output = capsys.readouterr().out
    assert "Executable: not found in PATH" in output
    assert "Active key: not configured" in output
