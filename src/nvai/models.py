from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/z-ai/glm-5.2"


@dataclass(slots=True)
class ApiKeyRecord:
    name: str
    model: str
    api_key: str
    expiredate: datetime
    base_url: str = DEFAULT_BASE_URL
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    last_used_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now().astimezone()
        expire = self.expiredate
        if expire.tzinfo is None:
            expire = expire.astimezone()
        return now >= expire

    @property
    def masked_key(self) -> str:
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:6]}****{self.api_key[-4:]}"
