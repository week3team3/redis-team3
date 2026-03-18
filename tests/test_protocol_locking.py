from __future__ import annotations

import time

from tests.support import MiniRedisTCPTestCase


class MiniRedisLockingTests(MiniRedisTCPTestCase):
    def test_lock_unlock_flow(self) -> None:
        self.assertEqual(self.send("LOCK profile worker-a 2"), ":1")
        self.assertEqual(self.send("LOCK profile worker-b 2"), ":0")
        self.assertEqual(self.send("UNLOCK profile worker-b"), ":0")
        self.assertEqual(self.send("UNLOCK profile worker-a"), ":1")
        self.assertEqual(self.send("LOCK profile worker-b 2"), ":1")

    def test_lock_expires_and_can_be_reacquired(self) -> None:
        self.assertEqual(self.send("LOCK refresh owner-a 1"), ":1")
        time.sleep(1.2)
        self.assertEqual(self.send("LOCK refresh owner-b 1"), ":1")

    def test_same_owner_can_renew_lock(self) -> None:
        self.assertEqual(self.send("LOCK session owner-a 1"), ":1")
        self.assertEqual(self.send("LOCK session owner-a 2"), ":1")

    def test_lock_usage_errors(self) -> None:
        self.assertEqual(self.send("LOCK only-two args"), "-ERR usage: LOCK <key> <owner> <ttl_seconds>")
        self.assertEqual(self.send("LOCK key owner nope"), "-ERR ttl_seconds must be an integer")
        self.assertEqual(self.send("LOCK key owner 0"), "-ERR ttl_seconds must be positive")
        self.assertEqual(self.send("UNLOCK key"), "-ERR usage: UNLOCK <key> <owner>")
