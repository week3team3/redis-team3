from __future__ import annotations

import random
import time
import unittest

from mini_redis.store import MiniRedisStore


class MiniRedisStoreExpirationTests(unittest.TestCase):
    def test_ttl_reports_missing_and_non_expiring_keys(self) -> None:
        store = MiniRedisStore()

        self.assertEqual(store.ttl("missing"), -2)
        store.set("hello", "world")
        self.assertEqual(store.ttl("hello"), -1)

    def test_expire_with_jitter_uses_randomized_ttl(self) -> None:
        store = MiniRedisStore(rng=random.Random(0))
        store.set("cache", "warm")

        applied_ttl = store.expire_with_jitter("cache", 2, 2)

        self.assertEqual(applied_ttl, 3)
        self.assertIn(store.ttl("cache"), (3, 2))

    def test_expired_key_is_removed_lazily(self) -> None:
        store = MiniRedisStore()
        store.set("short", "lived")
        self.assertTrue(store.expire("short", 1))

        time.sleep(1.1)

        self.assertIsNone(store.get("short"))
        self.assertEqual(store.ttl("short"), -2)
