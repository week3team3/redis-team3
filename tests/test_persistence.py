from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from mini_redis.server import MiniRedisHandler, MiniRedisTCPServer
from mini_redis.store import MiniRedisStore
from tests.support import MiniRedisTCPTestCase


class MiniRedisPersistenceTests(MiniRedisTCPTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.aof_path = Path(self.temp_dir.name) / "appendonly.aof"
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        self.temp_dir.cleanup()

    def make_store(self) -> MiniRedisStore:
        return MiniRedisStore(aof_path=str(self.aof_path), invalidation_grace_seconds=1)

    def restart_server(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.server = MiniRedisTCPServer(
            ("127.0.0.1", self.port),
            MiniRedisHandler,
            store=self.make_store(),
            sweep_interval=self.sweep_interval,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def test_restart_restores_live_keys(self) -> None:
        self.assertEqual(self.send("SET persisted value"), "+OK")
        self.assertEqual(self.send("INCR counter"), ":1")
        self.assertEqual(self.send("HSET reservation user alice"), ":1")
        self.assertEqual(self.send("SADD joined user-a"), ":1")
        self.assertEqual(self.send("ZADD waiting-room 1 user-a"), ":1")

        self.restart_server()

        self.assertEqual(self.send("GET persisted"), "$value")
        self.assertEqual(self.send("GET counter"), "$1")
        self.assertEqual(self.send("HGET reservation user"), "$alice")
        self.assertEqual(self.send("SMEMBERS joined"), '$["user-a"]')
        self.assertEqual(self.send("ZRANGE waiting-room 0 -1"), '$["user-a"]')

    def test_restart_does_not_restore_deleted_key(self) -> None:
        self.assertEqual(self.send("SET doomed value"), "+OK")
        self.assertEqual(self.send("DEL doomed"), ":1")

        self.restart_server()

        self.assertEqual(self.send("GET doomed"), "$nil")
