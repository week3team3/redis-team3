from __future__ import annotations

import socket
import threading
import unittest

from mini_redis.server import MiniRedisHandler, MiniRedisTCPServer
from mini_redis.store import MiniRedisStore


class MiniRedisTCPTestCase(unittest.TestCase):
    sweep_interval = 0.1

    def make_store(self) -> MiniRedisStore:
        return MiniRedisStore()

    def setUp(self) -> None:
        self.server = MiniRedisTCPServer(
            ("127.0.0.1", 0),
            MiniRedisHandler,
            store=self.make_store(),
            sweep_interval=self.sweep_interval,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def send(self, command: str) -> str:
        with socket.create_connection((self.host, self.port), timeout=2) as client:
            client.sendall(f"{command}\n".encode("utf-8"))
            data = client.recv(4096)
        return data.decode("utf-8").strip()
