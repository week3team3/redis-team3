from __future__ import annotations

import time

from mini_redis.store import MiniRedisStore
from tests.support import MiniRedisTCPTestCase


class MiniRedisInvalidationTests(MiniRedisTCPTestCase):
    def make_store(self) -> MiniRedisStore:
        return MiniRedisStore(invalidation_grace_seconds=1)

    def test_invalidated_key_behaves_like_missing(self) -> None:
        self.assertEqual(self.send("SET profile cached"), "+OK")
        self.assertEqual(self.send("INVALIDATE profile stale data"), ":1")
        self.assertEqual(self.send("GET profile"), "$nil")
        self.assertEqual(self.send("EXISTS profile"), ":0")
        self.assertEqual(self.send("TTL profile"), ":-2")

    def test_invalidated_key_is_purged_by_sweeper(self) -> None:
        self.assertEqual(self.send("SET temp data"), "+OK")
        self.assertEqual(self.send("INVALIDATE temp refresh"), ":1")

        time.sleep(1.3)

        self.assertEqual(self.server.store.size(), 0)

    def test_invalidate_usage_error(self) -> None:
        self.assertEqual(self.send("INVALIDATE"), "-ERR usage: INVALIDATE <key> [reason]")
