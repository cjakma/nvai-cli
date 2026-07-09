from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from nvai.models import ApiKeyRecord
from nvai.nvidia_client import NvidiaApiError, NvidiaClient
from nvai.runtime_config import DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT, default_max_tokens, default_timeout, parse_max_tokens, parse_timeout


def _key() -> ApiKeyRecord:
    return ApiKeyRecord(
        name="k",
        model="z-ai/glm-5.2",
        api_key="secret",
        expiredate=datetime.now().astimezone() + timedelta(days=1),
    )


def test_default_max_tokens_is_responsive_for_glm_52():
    assert DEFAULT_MAX_TOKENS == 1024
    assert DEFAULT_TIMEOUT == 180.0


def test_parse_max_tokens_bounds():
    assert parse_max_tokens("128") == 128
    with pytest.raises(ValueError):
        parse_max_tokens("0")
    with pytest.raises(ValueError):
        parse_max_tokens("8193")


def test_parse_timeout_bounds():
    assert parse_timeout("30") == 30.0
    with pytest.raises(ValueError):
        parse_timeout("4")
    with pytest.raises(ValueError):
        parse_timeout("601")


def test_default_max_tokens_reads_environment(monkeypatch):
    monkeypatch.setenv("NVAI_MAX_TOKENS", "256")
    assert default_max_tokens() == 256


def test_default_timeout_reads_environment(monkeypatch):
    monkeypatch.setenv("NVAI_TIMEOUT", "45")
    assert default_timeout() == 45.0


def test_chat_uses_responsive_default_max_tokens():
    client = NvidiaClient(_key())

    def fake_request(self, method, path, payload):
        assert payload["max_tokens"] == DEFAULT_MAX_TOKENS
        return {"choices": [{"message": {"content": "ok"}}]}

    with patch.object(NvidiaClient, "_request", fake_request):
        assert client.chat([{"role": "user", "content": "hi"}]) == "ok"


def test_timeout_is_reported_as_nvidia_api_error():
    client = NvidiaClient(_key(), timeout=3)
    with patch("urllib.request.urlopen", side_effect=TimeoutError("slow")):
        with pytest.raises(NvidiaApiError, match="timed out after 3s"):
            client.chat([{"role": "user", "content": "hi"}])
