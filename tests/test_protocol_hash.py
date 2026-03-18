from __future__ import annotations

from tests.support import MiniRedisTCPTestCase


class MiniRedisHashTests(MiniRedisTCPTestCase):
    def test_hset_hget_hgetall_hdel(self) -> None:
        self.assertEqual(self.send("HSET user:1 name alice"), ":1")
        self.assertEqual(self.send("HSET user:1 grade vip"), ":1")
        self.assertEqual(self.send("HSET user:1 grade vvip"), ":0")
        self.assertEqual(self.send("HGET user:1 name"), "$alice")
        self.assertEqual(self.send("HGET user:1 missing"), "$nil")
        self.assertEqual(self.send("HGETALL user:1"), '${"grade":"vvip","name":"alice"}')
        self.assertEqual(self.send("HDEL user:1 name"), ":1")
        self.assertEqual(self.send("HDEL user:1 name"), ":0")
        self.assertEqual(self.send("HGETALL user:1"), '${"grade":"vvip"}')

    def test_hash_wrongtype_errors(self) -> None:
        self.assertEqual(self.send("SET plain hello"), "+OK")
        self.assertEqual(self.send("HSET plain field value"), "-ERR wrong type for operation")
        self.assertEqual(self.send("HGET plain field"), "-ERR wrong type for operation")

    def test_hash_usage_errors(self) -> None:
        self.assertEqual(self.send("HSET user onlyfield"), "-ERR usage: HSET <key> <field> <value>")
        self.assertEqual(self.send("HGET user"), "-ERR usage: HGET <key> <field>")
        self.assertEqual(self.send("HDEL user"), "-ERR usage: HDEL <key> <field>")
        self.assertEqual(self.send("HGETALL user extra"), "-ERR usage: HGETALL <key>")
