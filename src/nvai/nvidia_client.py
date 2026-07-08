from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from .models import ApiKeyRecord


class NvidiaApiError(RuntimeError):
    pass


@dataclass(slots=True)
class NvidiaClient:
    key: ApiKeyRecord
    timeout: float = 60.0

    def _url(self, path: str) -> str:
        return self.key.base_url.rstrip("/") + "/" + path.lstrip("/")

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(path),
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.key.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401:
                raise NvidiaApiError(
                    "NVIDIA API rejected the key (401). Refresh the key with `nvai auth refresh`."
                ) from exc
            if exc.code == 403:
                raise NvidiaApiError("NVIDIA API denied access (403). Check model/key permissions.") from exc
            if exc.code == 404:
                raise NvidiaApiError("NVIDIA endpoint or model was not found (404). Check base_url/model.") from exc
            if exc.code == 429:
                raise NvidiaApiError("NVIDIA API rate limit hit (429). Wait and retry.") from exc
            raise NvidiaApiError(f"NVIDIA API HTTP {exc.code}: {details[:500]}") from exc
        except urllib.error.URLError as exc:
            raise NvidiaApiError(f"NVIDIA API network error: {exc.reason}") from exc

    def list_models(self) -> list[str]:
        data = self._request("GET", "/models")
        models = []
        for item in data.get("data", []):
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
        return models

    def validate_key(self, *, require_model: bool = False) -> tuple[bool, str]:
        models = self.list_models()
        if require_model and self.key.model not in models:
            return False, f"Key works, but model {self.key.model!r} was not listed."
        return True, "OK"

    def chat(self, messages: Iterable[dict], *, max_tokens: int = 8192, temperature: float = 0.2) -> str:
        payload = {
            "model": self.key.model,
            "messages": list(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        data = self._request("POST", "/chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise NvidiaApiError(f"Unexpected NVIDIA response shape: {json.dumps(data)[:500]}") from exc
