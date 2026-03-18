from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    redis_host: str = "127.0.0.1"
    redis_port: int = 6380
    hold_ttl_seconds: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_host=os.getenv("TICKETING_API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("TICKETING_API_PORT", "8000")),
            redis_host=os.getenv("MINI_REDIS_HOST", "127.0.0.1"),
            redis_port=int(os.getenv("MINI_REDIS_PORT", "6380")),
            hold_ttl_seconds=int(os.getenv("HOLD_TTL_SECONDS", "30")),
        )
