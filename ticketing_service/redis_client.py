from __future__ import annotations

import json
import socket
from dataclasses import dataclass


class MiniRedisClientError(RuntimeError):
    pass


@dataclass
class RateLimitReply:
    allowed: bool
    remaining: int
    reset_in: int
    count: int


class MiniRedisClient:
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._reader = None
        self._writer = None

    def __enter__(self) -> "MiniRedisClient":
        self._socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._reader = self._socket.makefile("r", encoding="utf-8", newline="\n")
        self._writer = self._socket.makefile("w", encoding="utf-8", newline="\n")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._writer is not None:
                self._writer.close()
        finally:
            try:
                if self._reader is not None:
                    self._reader.close()
            finally:
                if self._socket is not None:
                    self._socket.close()

    def execute(self, command: str) -> str:
        if self._writer is None or self._reader is None:
            raise RuntimeError("MiniRedisClient must be used as a context manager")
        self._writer.write(f"{command}\n")
        self._writer.flush()
        response = self._reader.readline().strip()
        if response.startswith("-ERR "):
            raise MiniRedisClientError(response[5:])
        return response

    def set(self, key: str, value: str, nx: bool = False) -> bool:
        response = self.execute(f"SET {key} {value}" + (" NX" if nx else ""))
        return response == "+OK"

    def get(self, key: str) -> str | None:
        response = self.execute(f"GET {key}")
        if response == "$nil":
            return None
        return response[1:]

    def delete(self, key: str) -> bool:
        return self.execute(f"DEL {key}") == ":1"

    def exists(self, key: str) -> bool:
        return self.execute(f"EXISTS {key}") == ":1"

    def incr(self, key: str) -> int:
        return int(self.execute(f"INCR {key}")[1:])

    def decr(self, key: str) -> int:
        return int(self.execute(f"DECR {key}")[1:])

    def incrby(self, key: str, amount: int) -> int:
        return int(self.execute(f"INCRBY {key} {amount}")[1:])

    def decrby(self, key: str, amount: int) -> int:
        return int(self.execute(f"DECRBY {key} {amount}")[1:])

    def expire(self, key: str, seconds: int) -> bool:
        return self.execute(f"EXPIRE {key} {seconds}") == ":1"

    def ttl(self, key: str) -> int:
        return int(self.execute(f"TTL {key}")[1:])

    def sadd(self, key: str, member: str) -> int:
        return int(self.execute(f"SADD {key} {member}")[1:])

    def srem(self, key: str, member: str) -> int:
        return int(self.execute(f"SREM {key} {member}")[1:])

    def sismember(self, key: str, member: str) -> bool:
        return self.execute(f"SISMEMBER {key} {member}") == ":1"

    def smembers(self, key: str) -> list[str]:
        response = self.execute(f"SMEMBERS {key}")
        if response == "$nil":
            return []
        return list(json.loads(response[1:]))

    def hset(self, key: str, field: str, value: str) -> int:
        return int(self.execute(f"HSET {key} {field} {value}")[1:])

    def hget(self, key: str, field: str) -> str | None:
        response = self.execute(f"HGET {key} {field}")
        if response == "$nil":
            return None
        return response[1:]

    def hgetall(self, key: str) -> dict[str, str]:
        response = self.execute(f"HGETALL {key}")
        if response == "$nil":
            return {}
        return dict(json.loads(response[1:]))

    def zadd(self, key: str, score: float, member: str) -> int:
        return int(self.execute(f"ZADD {key} {score} {member}")[1:])

    def zrank(self, key: str, member: str) -> int:
        return int(self.execute(f"ZRANK {key} {member}")[1:])

    def zrange(self, key: str, start: int, stop: int) -> list[str]:
        response = self.execute(f"ZRANGE {key} {start} {stop}")
        if response == "$nil":
            return []
        return list(json.loads(response[1:]))

    def zrem(self, key: str, member: str) -> int:
        return int(self.execute(f"ZREM {key} {member}")[1:])

    def zpopmin(self, key: str) -> tuple[str, float] | None:
        response = self.execute(f"ZPOPMIN {key}")
        if response == "$nil":
            return None
        member, score = json.loads(response[1:])
        return str(member), float(score)

    def zcard(self, key: str) -> int:
        return int(self.execute(f"ZCARD {key}")[1:])

    def lock(self, key: str, owner: str, ttl_seconds: int) -> bool:
        return self.execute(f"LOCK {key} {owner} {ttl_seconds}") == ":1"

    def unlock(self, key: str, owner: str) -> bool:
        return self.execute(f"UNLOCK {key} {owner}") == ":1"

    def ratecheck(self, key: str, limit: int, window_seconds: int) -> RateLimitReply:
        response = self.execute(f"RATECHECK {key} {limit} {window_seconds}")
        parts = response.split()
        allowed = parts[0] == "+ALLOWED"
        values = {}
        for token in parts[1:]:
            name, raw_value = token.split("=", 1)
            values[name] = int(raw_value)
        return RateLimitReply(
            allowed=allowed,
            remaining=values["remaining"],
            reset_in=values["reset_in"],
            count=values["count"],
        )
