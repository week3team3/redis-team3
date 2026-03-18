from __future__ import annotations

from tests.support import MiniRedisTCPTestCase


class MiniRedisSetTests(MiniRedisTCPTestCase):
    def test_sadd_sismember_srem_smembers(self) -> None:
        self.assertEqual(self.send("SADD queue:joined user-a"), ":1")
        self.assertEqual(self.send("SADD queue:joined user-b"), ":1")
        self.assertEqual(self.send("SADD queue:joined user-a"), ":0")
        self.assertEqual(self.send("SISMEMBER queue:joined user-a"), ":1")
        self.assertEqual(self.send("SISMEMBER queue:joined user-c"), ":0")
        self.assertEqual(self.send("SMEMBERS queue:joined"), '$["user-a","user-b"]')
        self.assertEqual(self.send("SREM queue:joined user-a"), ":1")
        self.assertEqual(self.send("SREM queue:joined user-a"), ":0")
        self.assertEqual(self.send("SMEMBERS queue:joined"), '$["user-b"]')

    def test_set_wrongtype_errors(self) -> None:
        self.assertEqual(self.send("SET plain hello"), "+OK")
        self.assertEqual(self.send("SADD plain user-a"), "-ERR wrong type for operation")
        self.assertEqual(self.send("SMEMBERS plain"), "-ERR wrong type for operation")

    def test_set_usage_errors(self) -> None:
        self.assertEqual(self.send("SADD onlykey"), "-ERR usage: SADD <key> <member>")
        self.assertEqual(self.send("SISMEMBER onlykey"), "-ERR usage: SISMEMBER <key> <member>")
        self.assertEqual(self.send("SREM onlykey"), "-ERR usage: SREM <key> <member>")
        self.assertEqual(self.send("SMEMBERS key extra"), "-ERR usage: SMEMBERS <key>")
