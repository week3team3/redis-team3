from __future__ import annotations

from tests.support import MiniRedisTCPTestCase


class MiniRedisBasicCommandTests(MiniRedisTCPTestCase):
    def test_ping(self) -> None:
        self.assertEqual(self.send("PING"), "+PONG")

    def test_set_get_delete_flow(self) -> None:
        self.assertEqual(self.send("SET greeting hello world"), "+OK")
        self.assertEqual(self.send("GET greeting"), "$hello world")
        self.assertEqual(self.send("EXISTS greeting"), ":1")
        self.assertEqual(self.send("DEL greeting"), ":1")
        self.assertEqual(self.send("GET greeting"), "$nil")
        self.assertEqual(self.send("EXISTS greeting"), ":0")

    def test_set_overwrites_and_clears_previous_state(self) -> None:
        self.assertEqual(self.send("SET key first"), "+OK")
        self.assertEqual(self.send("EXPIRE key 10"), ":1")
        self.assertEqual(self.send("INVALIDATE key manual"), ":1")
        self.assertEqual(self.send("SET key second"), "+OK")
        self.assertEqual(self.send("GET key"), "$second")
        self.assertEqual(self.send("TTL key"), ":-1")

    def test_usage_errors(self) -> None:
        self.assertEqual(self.send("SET only-key"), "-ERR usage: SET <key> <value>")
        self.assertEqual(self.send("GET a b"), "-ERR usage: GET <key>")
        self.assertEqual(self.send("DEL a b"), "-ERR usage: DEL <key>")
        self.assertEqual(self.send("EXISTS"), "-ERR usage: EXISTS <key>")
        self.assertEqual(self.send("UNKNOWN"), "-ERR unknown command 'UNKNOWN'")
