from __future__ import annotations

import time

from tests.support import MiniRedisTCPTestCase


class MiniRedisRateLimitTests(MiniRedisTCPTestCase):
    def test_ratecheck_allows_until_limit_then_blocks(self) -> None:
        self.assertEqual(
            self.send("RATECHECK api:user:1 2 2"),
            "+ALLOWED remaining=1 reset_in=2 count=1",
        )
        self.assertEqual(
            self.send("RATECHECK api:user:1 2 2"),
            "+ALLOWED remaining=0 reset_in=2 count=2",
        )
        blocked_reply = self.send("RATECHECK api:user:1 2 2")
        self.assertTrue(blocked_reply.startswith("+BLOCKED remaining=0 reset_in="))
        self.assertTrue(blocked_reply.endswith(" count=2"))

    def test_ratecheck_resets_after_window(self) -> None:
        self.assertEqual(
            self.send("RATECHECK api:user:2 1 1"),
            "+ALLOWED remaining=0 reset_in=1 count=1",
        )
        self.assertTrue(self.send("RATECHECK api:user:2 1 1").startswith("+BLOCKED"))

        time.sleep(1.2)

        self.assertEqual(
            self.send("RATECHECK api:user:2 1 1"),
            "+ALLOWED remaining=0 reset_in=1 count=1",
        )

    def test_ratecheck_usage_errors(self) -> None:
        self.assertEqual(
            self.send("RATECHECK missing pieces"),
            "-ERR usage: RATECHECK <key> <limit> <window_seconds>",
        )
        self.assertEqual(
            self.send("RATECHECK api:user nope 1"),
            "-ERR limit and window_seconds must be integers",
        )
        self.assertEqual(
            self.send("RATECHECK api:user 0 1"),
            "-ERR limit must be positive",
        )
        self.assertEqual(
            self.send("RATECHECK api:user 1 0"),
            "-ERR window_seconds must be positive",
        )
