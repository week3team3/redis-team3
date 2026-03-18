from __future__ import annotations

from tests.support import MiniRedisTCPTestCase


class MiniRedisCounterTests(MiniRedisTCPTestCase):
    def test_incr_creates_and_increments_counter(self) -> None:
        self.assertEqual(self.send("INCR visits"), ":1")
        self.assertEqual(self.send("INCR visits"), ":2")
        self.assertEqual(self.send("GET visits"), "$2")

    def test_incrby_and_decrby(self) -> None:
        self.assertEqual(self.send("INCRBY stock 10"), ":10")
        self.assertEqual(self.send("DECRBY stock 3"), ":7")
        self.assertEqual(self.send("GET stock"), "$7")

    def test_decr_decrements_by_one(self) -> None:
        self.assertEqual(self.send("INCRBY remaining 3"), ":3")
        self.assertEqual(self.send("DECR remaining"), ":2")
        self.assertEqual(self.send("DECR remaining"), ":1")
        self.assertEqual(self.send("GET remaining"), "$1")

    def test_incr_rejects_non_integer_values(self) -> None:
        self.assertEqual(self.send("SET notanumber hello"), "+OK")
        self.assertEqual(self.send("INCR notanumber"), "-ERR value is not an integer")
        self.assertEqual(self.send("DECR notanumber"), "-ERR value is not an integer")
        self.assertEqual(self.send("INCRBY notanumber 2"), "-ERR value is not an integer")
        self.assertEqual(self.send("DECRBY notanumber 1"), "-ERR value is not an integer")

    def test_incr_usage_error(self) -> None:
        self.assertEqual(self.send("INCR"), "-ERR usage: INCR <key>")
        self.assertEqual(self.send("DECR"), "-ERR usage: DECR <key>")
        self.assertEqual(self.send("INCRBY"), "-ERR usage: INCRBY <key> <amount>")
        self.assertEqual(self.send("INCRBY count nope"), "-ERR amount must be an integer")
        self.assertEqual(self.send("DECRBY"), "-ERR usage: DECRBY <key> <amount>")
        self.assertEqual(self.send("DECRBY count nope"), "-ERR amount must be an integer")
        self.assertEqual(self.send("DECRBY count -1"), "-ERR amount must be non-negative")
