from __future__ import annotations

from mini_redis.store import RedisStore


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_store_expires_keys_lazily() -> None:
    clock = FakeClock()
    store = RedisStore(clock=clock)

    assert store.set("seat", "HELD:user-1", ex=5) is True
    assert store.ttl("seat") == 5

    clock.advance(6)

    assert store.get("seat") is None
    assert store.exists("seat") == 0
    assert store.ttl("seat") == -2


def test_store_supports_nx_and_conditional_updates() -> None:
    store = RedisStore()

    assert store.set("key", "value", nx=True) is True
    assert store.set("key", "other", nx=True) is False
    assert store.set_if_eq("key", "value", "next") is True
    assert store.del_if_eq("key", "value") is False
    assert store.del_if_eq("key", "next") is True


def test_cleanup_expired_returns_removed_count() -> None:
    clock = FakeClock()
    store = RedisStore(clock=clock)

    store.set("a", "1", ex=1)
    store.set("b", "2", ex=5)
    clock.advance(2)

    assert store.cleanup_expired() == 1
    assert store.get("a") is None
    assert store.get("b") == "2"
