import fnmatch
import threading
import time


class Store:
    def __init__(self):
        self.data = {}
        self.expirations = {}
        self.lock = threading.RLock()

    def _purge_if_expired(self, key):
        expires_at = self.expirations.get(key)
        if expires_at is None:
            return

        if expires_at <= time.time():
            self.data.pop(key, None)
            self.expirations.pop(key, None)

    def _cleanup_expired_keys(self):
        expired_keys = []
        now = time.time()
        for key, expires_at in self.expirations.items():
            if expires_at <= now:
                expired_keys.append(key)

        for key in expired_keys:
            self.data.pop(key, None)
            self.expirations.pop(key, None)

    def _key_exists(self, key):
        self._purge_if_expired(key)
        return key in self.data

    def _read_int(self, key):
        self._purge_if_expired(key)
        raw = self.data.get(key, "0")
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("value is not an integer") from exc

    def set(self, key, value):
        with self.lock:
            self.data[key] = str(value)
            self.expirations.pop(key, None)
            return "OK"

    def setnx(self, key, value):
        with self.lock:
            if self._key_exists(key):
                return 0
            self.data[key] = str(value)
            self.expirations.pop(key, None)
            return 1

    def get(self, key):
        with self.lock:
            self._purge_if_expired(key)
            return self.data.get(key, "(nil)")

    def getset(self, key, value):
        with self.lock:
            old_value = self.get(key)
            self.data[key] = str(value)
            self.expirations.pop(key, None)
            return old_value

    def delete(self, *keys):
        with self.lock:
            deleted = 0
            for key in keys:
                self._purge_if_expired(key)
                if key in self.data:
                    self.data.pop(key, None)
                    self.expirations.pop(key, None)
                    deleted += 1
            return deleted

    def exists(self, key):
        with self.lock:
            return 1 if self._key_exists(key) else 0

    def type_of(self, key):
        with self.lock:
            return "string" if self._key_exists(key) else "none"

    def increment(self, key):
        return self.increment_by(key, 1)

    def decrement(self, key):
        return self.decrement_by(key, 1)

    def increment_by(self, key, amount):
        with self.lock:
            try:
                delta = int(amount)
            except ValueError as exc:
                raise ValueError("increment is not an integer") from exc

            value = self._read_int(key) + delta
            self.data[key] = str(value)
            return value

    def decrement_by(self, key, amount):
        with self.lock:
            try:
                delta = int(amount)
            except ValueError as exc:
                raise ValueError("decrement is not an integer") from exc

            value = self._read_int(key) - delta
            self.data[key] = str(value)
            return value

    def mget(self, *keys):
        with self.lock:
            return [self.get(key) for key in keys]

    def mset(self, *args):
        with self.lock:
            for index in range(0, len(args), 2):
                key = args[index]
                value = args[index + 1]
                self.data[key] = str(value)
                self.expirations.pop(key, None)
            return "OK"

    def expire(self, key, seconds):
        with self.lock:
            self._purge_if_expired(key)
            if key not in self.data:
                return 0

            try:
                ttl_seconds = int(seconds)
            except ValueError as exc:
                raise ValueError("expire time is not an integer") from exc

            self.expirations[key] = time.time() + ttl_seconds
            return 1

    def ttl(self, key):
        with self.lock:
            self._purge_if_expired(key)
            if key not in self.data:
                return -2
            if key not in self.expirations:
                return -1
            remaining = int(self.expirations[key] - time.time())
            return remaining if remaining >= 0 else -2

    def persist(self, key):
        with self.lock:
            self._purge_if_expired(key)
            if key in self.data and key in self.expirations:
                self.expirations.pop(key, None)
                return 1
            return 0

    def append(self, key, value):
        with self.lock:
            self._purge_if_expired(key)
            current = self.data.get(key, "")
            updated = f"{current}{value}"
            self.data[key] = updated
            return len(updated)

    def strlen(self, key):
        with self.lock:
            self._purge_if_expired(key)
            return len(self.data.get(key, ""))

    def flushdb(self):
        with self.lock:
            self.data.clear()
            self.expirations.clear()
            return "OK"

    def keys(self, pattern):
        with self.lock:
            self._cleanup_expired_keys()
            return sorted([key for key in self.data if fnmatch.fnmatch(key, pattern)])

    def scan(self, cursor):
        with self.lock:
            self._cleanup_expired_keys()
            try:
                index = int(cursor)
            except ValueError as exc:
                raise ValueError("invalid cursor") from exc

            if index < 0:
                raise ValueError("invalid cursor")

            keys = sorted(self.data.keys())
            batch = keys[index:index + 10]
            next_cursor = 0 if index + 10 >= len(keys) else index + 10
            return [str(next_cursor), batch]

    def dbsize(self):
        with self.lock:
            self._cleanup_expired_keys()
            return len(self.data)

    def info(self):
        with self.lock:
            self._cleanup_expired_keys()
            lines = [
                "# Server",
                "redis_version:virtual-1.0",
                "tcp_port:6379",
                "# Keyspace",
                f"keys:{len(self.data)}",
                f"expires:{len(self.expirations)}",
            ]
            return "\n".join(lines)
