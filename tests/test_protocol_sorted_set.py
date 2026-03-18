from __future__ import annotations

from tests.support import MiniRedisTCPTestCase


class MiniRedisSortedSetTests(MiniRedisTCPTestCase):
    def test_zadd_zrank_zrange_zrem_zpopmin(self) -> None:
        self.assertEqual(self.send("ZADD waiting-room 10.0 user-c"), ":1")
        self.assertEqual(self.send("ZADD waiting-room 5.0 user-a"), ":1")
        self.assertEqual(self.send("ZADD waiting-room 7.0 user-b"), ":1")
        self.assertEqual(self.send("ZADD waiting-room 5.0 user-a"), ":0")
        self.assertEqual(self.send("ZRANK waiting-room user-a"), ":0")
        self.assertEqual(self.send("ZRANK waiting-room user-b"), ":1")
        self.assertEqual(self.send("ZRANGE waiting-room 0 -1"), '$["user-a","user-b","user-c"]')
        self.assertEqual(self.send("ZCARD waiting-room"), ":3")
        self.assertEqual(self.send("ZPOPMIN waiting-room"), '$["user-a",5.0]')
        self.assertEqual(self.send("ZREM waiting-room user-c"), ":1")
        self.assertEqual(self.send("ZRANGE waiting-room 0 -1"), '$["user-b"]')

    def test_sorted_set_wrongtype_errors(self) -> None:
        self.assertEqual(self.send("SET plain hello"), "+OK")
        self.assertEqual(self.send("ZADD plain 1.0 user"), "-ERR wrong type for operation")
        self.assertEqual(self.send("ZRANGE plain 0 -1"), "-ERR wrong type for operation")

    def test_sorted_set_usage_errors(self) -> None:
        self.assertEqual(self.send("ZADD queue 1"), "-ERR usage: ZADD <key> <score> <member>")
        self.assertEqual(self.send("ZADD queue nope user"), "-ERR score must be a number")
        self.assertEqual(self.send("ZRANK queue"), "-ERR usage: ZRANK <key> <member>")
        self.assertEqual(self.send("ZRANGE queue 0"), "-ERR usage: ZRANGE <key> <start> <stop>")
        self.assertEqual(self.send("ZRANGE queue zero one"), "-ERR start and stop must be integers")
        self.assertEqual(self.send("ZREM queue"), "-ERR usage: ZREM <key> <member>")
        self.assertEqual(self.send("ZPOPMIN queue extra"), "-ERR usage: ZPOPMIN <key>")
        self.assertEqual(self.send("ZCARD queue extra"), "-ERR usage: ZCARD <key>")
