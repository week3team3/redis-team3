from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any

from mini_redis.hash_table import HashTable
from mini_redis.persistence import AOFPersistence


WRONGTYPE_ERROR = "wrong type for operation"


@dataclass
class Entry:
    data_type: str
    value: Any
    expires_at: float | None = None
    invalidated: bool = False
    invalidation_reason: str | None = None
    invalidated_at: float | None = None

    def to_record(self) -> dict[str, object]:
        return {
            "data_type": self.data_type,
            "value": _serialize_value(self.data_type, self.value),
            "expires_at": self.expires_at,
            "invalidated": self.invalidated,
            "invalidation_reason": self.invalidation_reason,
            "invalidated_at": self.invalidated_at,
        }

    @classmethod
    def from_record(cls, payload: dict[str, object]) -> "Entry":
        data_type = str(payload["data_type"])
        return cls(
            data_type=data_type,
            value=_deserialize_value(data_type, payload["value"]),
            expires_at=payload.get("expires_at"),
            invalidated=bool(payload.get("invalidated", False)),
            invalidation_reason=payload.get("invalidation_reason"),
            invalidated_at=payload.get("invalidated_at"),
        )


@dataclass
class LockEntry:
    owner: str
    expires_at: float


@dataclass
class RateLimitEntry:
    count: int
    window_end: float


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_in: int
    count: int


def _serialize_value(data_type: str, value: Any) -> Any:
    if data_type == "string":
        return value
    if data_type in {"hash", "set", "zset"}:
        return value.items()
    raise ValueError(f"unsupported data_type {data_type}")


def _deserialize_value(data_type: str, payload: Any) -> Any:
    if data_type == "string":
        return str(payload)
    table = HashTable()
    if data_type == "hash":
        for field, field_value in payload:
            table.set(str(field), str(field_value))
        return table
    if data_type == "set":
        for member, _ in payload:
            table.set(str(member), True)
        return table
    if data_type == "zset":
        for member, score in payload:
            table.set(str(member), float(score))
        return table
    raise ValueError(f"unsupported data_type {data_type}")


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


class MiniRedisStore:
    """Thread-safe wrapper around the custom hash table."""

    def __init__(
        self,
        rng: random.Random | None = None,
        aof_path: str | None = None,
        invalidation_grace_seconds: int = 30,
    ) -> None:
        self._table = HashTable()
        self._locks = HashTable()
        self._rate_limits = HashTable()
        self._lock = RLock()
        self._rng = rng or random.Random()
        self._persistence = AOFPersistence(aof_path)
        self._invalidation_grace_seconds = invalidation_grace_seconds
        self._restore_from_aof()

    def set(self, key: str, value: str) -> None:
        with self._lock:
            entry = Entry(data_type="string", value=value)
            self._table.set(key, entry)
            self._persist_upsert(key, entry)

    def setnx(self, key: str, value: str) -> bool:
        with self._lock:
            if self._get_visible_entry(key) is not None:
                return False
            entry = Entry(data_type="string", value=value)
            self._table.set(key, entry)
            self._persist_upsert(key, entry)
            return True

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            if entry.data_type != "string":
                raise ValueError(WRONGTYPE_ERROR)
            return str(entry.value)

    def exists(self, key: str) -> bool:
        with self._lock:
            return self._get_visible_entry(key) is not None

    def delete(self, key: str) -> bool:
        with self._lock:
            deleted = self._table.delete(key)
            if deleted:
                self._persistence.append_delete(key)
            return deleted

    def expire(self, key: str, seconds: int) -> bool:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return False
            entry.expires_at = time.time() + seconds
            self._persist_upsert(key, entry)
            return True

    def expire_with_jitter(self, key: str, seconds: int, jitter_seconds: int) -> int:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        if jitter_seconds < 0:
            raise ValueError("jitter_seconds must be non-negative")
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            actual_seconds = seconds + self._rng.randint(0, jitter_seconds)
            entry.expires_at = time.time() + actual_seconds
            self._persist_upsert(key, entry)
            return actual_seconds

    def ttl(self, key: str) -> int:
        with self._lock:
            entry = self._table.get(key)
            if entry is None:
                return -2
            if self._is_unavailable(entry):
                self._purge_if_needed(key, entry)
                return -2
            if entry.expires_at is None:
                return -1
            remaining = entry.expires_at - time.time()
            if remaining <= 0:
                self._purge_if_needed(key, entry)
                return -2
            return math.ceil(remaining)

    def incr(self, key: str) -> int:
        return self.incrby(key, 1)

    def incrby(self, key: str, amount: int) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                value = amount
                entry = Entry(data_type="string", value=str(value))
                self._table.set(key, entry)
                self._persist_upsert(key, entry)
                return value

            if entry.data_type != "string":
                raise ValueError(WRONGTYPE_ERROR)

            try:
                value = int(entry.value)
            except ValueError as exc:
                raise ValueError("value is not an integer") from exc

            value += amount
            entry.value = str(value)
            self._persist_upsert(key, entry)
            return value

    def decrby(self, key: str, amount: int) -> int:
        return self.incrby(key, -amount)

    def decr(self, key: str) -> int:
        return self.decrby(key, 1)

    def invalidate(self, key: str, reason: str | None = None) -> bool:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return False
            entry.invalidated = True
            entry.invalidation_reason = reason
            entry.invalidated_at = time.time()
            self._persist_upsert(key, entry)
            return True

    def hset(self, key: str, field: str, value: str) -> int:
        with self._lock:
            entry = self._get_or_create_entry(key, "hash")
            table: HashTable = entry.value
            created = 0 if table.contains(field) else 1
            table.set(field, value)
            self._persist_upsert(key, entry)
            return created

    def hget(self, key: str, field: str) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            self._assert_type(entry, "hash")
            table: HashTable = entry.value
            value = table.get(field)
            return None if value is None else str(value)

    def hdel(self, key: str, field: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            self._assert_type(entry, "hash")
            table: HashTable = entry.value
            deleted = table.delete(field)
            if deleted:
                if len(table) == 0:
                    self._table.delete(key)
                    self._persistence.append_delete(key)
                else:
                    self._persist_upsert(key, entry)
                return 1
            return 0

    def hgetall(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            self._assert_type(entry, "hash")
            table: HashTable = entry.value
            return _to_json({field: value for field, value in sorted(table.items())})

    def sadd(self, key: str, member: str) -> int:
        with self._lock:
            entry = self._get_or_create_entry(key, "set")
            table: HashTable = entry.value
            created = 0 if table.contains(member) else 1
            table.set(member, True)
            self._persist_upsert(key, entry)
            return created

    def sismember(self, key: str, member: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            self._assert_type(entry, "set")
            table: HashTable = entry.value
            return 1 if table.contains(member) else 0

    def srem(self, key: str, member: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            self._assert_type(entry, "set")
            table: HashTable = entry.value
            deleted = table.delete(member)
            if deleted:
                if len(table) == 0:
                    self._table.delete(key)
                    self._persistence.append_delete(key)
                else:
                    self._persist_upsert(key, entry)
                return 1
            return 0

    def smembers(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            self._assert_type(entry, "set")
            table: HashTable = entry.value
            members = sorted(member for member, _ in table.items())
            return _to_json(members)

    def zadd(self, key: str, score: float, member: str) -> int:
        with self._lock:
            entry = self._get_or_create_entry(key, "zset")
            table: HashTable = entry.value
            created = 0 if table.contains(member) else 1
            table.set(member, float(score))
            self._persist_upsert(key, entry)
            return created

    def zrank(self, key: str, member: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return -1
            self._assert_type(entry, "zset")
            ordered = self._sorted_zset(entry.value)
            for index, (current_member, _) in enumerate(ordered):
                if current_member == member:
                    return index
            return -1

    def zrange(self, key: str, start: int, stop: int) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            self._assert_type(entry, "zset")
            ordered = self._sorted_zset(entry.value)
            total = len(ordered)
            if total == 0:
                return _to_json([])
            normalized_start = start if start >= 0 else total + start
            normalized_stop = stop if stop >= 0 else total + stop
            normalized_start = max(normalized_start, 0)
            normalized_stop = min(normalized_stop, total - 1)
            if normalized_start > normalized_stop or normalized_start >= total:
                return _to_json([])
            members = [member for member, _ in ordered[normalized_start : normalized_stop + 1]]
            return _to_json(members)

    def zrem(self, key: str, member: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            self._assert_type(entry, "zset")
            table: HashTable = entry.value
            deleted = table.delete(member)
            if deleted:
                if len(table) == 0:
                    self._table.delete(key)
                    self._persistence.append_delete(key)
                else:
                    self._persist_upsert(key, entry)
                return 1
            return 0

    def zpopmin(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return None
            self._assert_type(entry, "zset")
            ordered = self._sorted_zset(entry.value)
            if not ordered:
                return None
            member, score = ordered[0]
            table: HashTable = entry.value
            table.delete(member)
            if len(table) == 0:
                self._table.delete(key)
                self._persistence.append_delete(key)
            else:
                self._persist_upsert(key, entry)
            return _to_json([member, score])

    def zcard(self, key: str) -> int:
        with self._lock:
            entry = self._get_visible_entry(key)
            if entry is None:
                return 0
            self._assert_type(entry, "zset")
            table: HashTable = entry.value
            return len(table)

    def cleanup(self) -> int:
        with self._lock:
            removed = 0
            for key, entry in list(self._table.items()):
                if self._should_purge(entry):
                    self._table.delete(key)
                    self._persistence.append_delete(key)
                    removed += 1
            now = time.time()
            for key, lock_entry in list(self._locks.items()):
                if lock_entry.expires_at <= now:
                    self._locks.delete(key)
                    removed += 1
            for key, rate_entry in list(self._rate_limits.items()):
                if rate_entry.window_end <= now:
                    self._rate_limits.delete(key)
                    removed += 1
            return removed

    def acquire_lock(self, key: str, owner: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        with self._lock:
            existing = self._locks.get(key)
            now = time.time()
            if existing is not None and existing.expires_at <= now:
                self._locks.delete(key)
                existing = None
            if existing is None or existing.owner == owner:
                self._locks.set(key, LockEntry(owner=owner, expires_at=now + ttl_seconds))
                return True
            return False

    def release_lock(self, key: str, owner: str) -> bool:
        with self._lock:
            existing = self._locks.get(key)
            now = time.time()
            if existing is None:
                return False
            if existing.expires_at <= now:
                self._locks.delete(key)
                return False
            if existing.owner != owner:
                return False
            self._locks.delete(key)
            return True

    def rate_check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        with self._lock:
            now = time.time()
            existing = self._rate_limits.get(key)
            if existing is None or existing.window_end <= now:
                existing = RateLimitEntry(count=1, window_end=now + window_seconds)
                self._rate_limits.set(key, existing)
                return RateLimitResult(
                    allowed=True,
                    remaining=max(limit - 1, 0),
                    reset_in=math.ceil(existing.window_end - now),
                    count=1,
                )
            if existing.count < limit:
                existing.count += 1
                return RateLimitResult(
                    allowed=True,
                    remaining=max(limit - existing.count, 0),
                    reset_in=max(math.ceil(existing.window_end - now), 0),
                    count=existing.count,
                )
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in=max(math.ceil(existing.window_end - now), 0),
                count=existing.count,
            )

    def size(self) -> int:
        with self._lock:
            return len(self._table)

    def _get_visible_entry(self, key: str) -> Entry | None:
        entry = self._table.get(key)
        if entry is None:
            return None
        if self._is_unavailable(entry):
            self._purge_if_needed(key, entry)
            return None
        return entry

    def _get_or_create_entry(self, key: str, data_type: str) -> Entry:
        entry = self._get_visible_entry(key)
        if entry is None:
            entry = Entry(data_type=data_type, value=self._new_value_for_type(data_type))
            self._table.set(key, entry)
            return entry
        self._assert_type(entry, data_type)
        return entry

    @staticmethod
    def _new_value_for_type(data_type: str) -> Any:
        if data_type == "string":
            return ""
        if data_type in {"hash", "set", "zset"}:
            return HashTable()
        raise ValueError(f"unsupported data_type {data_type}")

    @staticmethod
    def _assert_type(entry: Entry, expected: str) -> None:
        if entry.data_type != expected:
            raise ValueError(WRONGTYPE_ERROR)

    def _purge_if_needed(self, key: str, entry: Entry) -> None:
        if self._should_purge(entry):
            self._table.delete(key)
            self._persistence.append_delete(key)

    def _should_purge(self, entry: Entry) -> bool:
        if self._is_expired(entry):
            return True
        if entry.invalidated and entry.invalidated_at is not None:
            return time.time() >= entry.invalidated_at + self._invalidation_grace_seconds
        return False

    @staticmethod
    def _sorted_zset(table: HashTable) -> list[tuple[str, float]]:
        pairs = [(member, float(score)) for member, score in table.items()]
        return sorted(pairs, key=lambda item: (item[1], item[0]))

    @staticmethod
    def _is_expired(entry: Entry) -> bool:
        return entry.expires_at is not None and time.time() >= entry.expires_at

    @classmethod
    def _is_unavailable(cls, entry: Entry) -> bool:
        return entry.invalidated or cls._is_expired(entry)

    def _persist_upsert(self, key: str, entry: Entry) -> None:
        self._persistence.append_upsert(key, entry.to_record())

    def _restore_from_aof(self) -> None:
        for operation in self._persistence.load_operations():
            op = operation.get("op")
            key = operation.get("key")
            if not isinstance(key, str):
                continue
            if op == "delete":
                self._table.delete(key)
            elif op == "upsert":
                payload = operation.get("entry")
                if not isinstance(payload, dict):
                    continue
                entry = Entry.from_record(payload)
                if not self._should_purge(entry):
                    self._table.set(key, entry)
