from __future__ import annotations

import math
import time
from collections.abc import Callable


class RedisStore:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.time
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}

    def _now(self) -> float:
        return self._clock()

    def _purge_if_expired(self, key: str) -> bool:
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return False
        if expires_at > self._now():
            return False
        self._values.pop(key, None)
        self._expires_at.pop(key, None)
        return True

    def get(self, key: str) -> str | None:
        self._purge_if_expired(key)
        return self._values.get(key)

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        self._purge_if_expired(key)
        if nx and key in self._values:
            return False
        self._values[key] = value
        if ex is None:
            self._expires_at.pop(key, None)
        else:
            self._expires_at[key] = self._now() + ex
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            self._purge_if_expired(key)
            existed = key in self._values
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
            if existed:
                deleted += 1
        return deleted

    def exists(self, *keys: str) -> int:
        total = 0
        for key in keys:
            self._purge_if_expired(key)
            if key in self._values:
                total += 1
        return total

    def expire(self, key: str, seconds: int) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return 0
        if seconds <= 0:
            self.delete(key)
            return 1
        self._expires_at[key] = self._now() + seconds
        return 1

    def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        remaining = expires_at - self._now()
        if remaining <= 0:
            self.delete(key)
            return -2
        return max(0, math.ceil(remaining))

    def set_if_eq(self, key: str, expected: str, new_value: str) -> bool:
        self._purge_if_expired(key)
        if self._values.get(key) != expected:
            return False
        self._values[key] = new_value
        self._expires_at.pop(key, None)
        return True

    def del_if_eq(self, key: str, expected: str) -> bool:
        self._purge_if_expired(key)
        if self._values.get(key) != expected:
            return False
        self._values.pop(key, None)
        self._expires_at.pop(key, None)
        return True

    def cleanup_expired(self) -> int:
        expired_keys = [key for key in list(self._expires_at) if self._purge_if_expired(key)]
        return len(expired_keys)
