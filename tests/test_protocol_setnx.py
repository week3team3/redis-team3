from __future__ import annotations

import time

from tests.support import MiniRedisTCPTestCase


class MiniRedisSetNxTests(MiniRedisTCPTestCase):
    def test_set_nx_only_sets_missing_key(self) -> None:
        self.assertEqual(self.send("SET queue-token user-a NX"), "+OK")
        self.assertEqual(self.send("GET queue-token"), "$user-a")
        self.assertEqual(self.send("SET queue-token user-b NX"), "$nil")
        self.assertEqual(self.send("GET queue-token"), "$user-a")

    def test_set_nx_treats_expired_or_invalidated_key_as_missing(self) -> None:
        self.assertEqual(self.send("SET once first"), "+OK")
        self.assertEqual(self.send("EXPIRE once 1"), ":1")
        time.sleep(1.1)
        self.assertEqual(self.send("SET once second NX"), "+OK")
        self.assertEqual(self.send("GET once"), "$second")

        self.assertEqual(self.send("SET stale value"), "+OK")
        self.assertEqual(self.send("INVALIDATE stale manual"), ":1")
        self.assertEqual(self.send("SET stale refreshed NX"), "+OK")
        self.assertEqual(self.send("GET stale"), "$refreshed")

    def test_set_nx_usage_and_option_errors(self) -> None:
        self.assertEqual(self.send("SET"), "-ERR usage: SET <key> <value>")
        self.assertEqual(self.send("SET only-key"), "-ERR usage: SET <key> <value>")
