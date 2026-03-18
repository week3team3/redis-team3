from __future__ import annotations

import time

from tests.support import MiniRedisTCPTestCase


class MiniRedisExpirationTests(MiniRedisTCPTestCase):
    def test_expire_and_ttl(self) -> None:
        self.assertEqual(self.send("SET session active"), "+OK")
        self.assertEqual(self.send("TTL session"), ":-1")
        self.assertEqual(self.send("EXPIRE session 1"), ":1")
        self.assertIn(int(self.send("TTL session")[1:]), (0, 1))

        time.sleep(1.2)

        self.assertEqual(self.send("GET session"), "$nil")
        self.assertEqual(self.send("TTL session"), ":-2")
        self.assertEqual(self.send("EXISTS session"), ":0")

    def test_expire_jitter_applies_ttl_in_range(self) -> None:
        self.assertEqual(self.send("SET cache warm"), "+OK")
        applied_ttl = int(self.send("EXPIREJITTER cache 1 1")[1:])

        self.assertIn(applied_ttl, (1, 2))
        observed_ttl = int(self.send("TTL cache")[1:])
        self.assertGreaterEqual(observed_ttl, 1)
        self.assertLessEqual(observed_ttl, 2)

    def test_expire_validates_arguments(self) -> None:
        self.assertEqual(self.send("EXPIRE missing 0"), "-ERR seconds must be positive")
        self.assertEqual(self.send("EXPIRE missing nope"), "-ERR seconds must be an integer")
        self.assertEqual(
            self.send("EXPIREJITTER missing one 1"),
            "-ERR seconds and jitter_seconds must be integers",
        )
        self.assertEqual(
            self.send("EXPIREJITTER missing 1 -1"),
            "-ERR jitter_seconds must be non-negative",
        )
