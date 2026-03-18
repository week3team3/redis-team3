from __future__ import annotations

from mini_redis.cli import send_command
from tests.support import MiniRedisTCPTestCase


class MiniRedisCLITests(MiniRedisTCPTestCase):
    def test_send_command_ping(self) -> None:
        self.assertEqual(send_command(self.host, self.port, "PING"), "+PONG")

    def test_send_command_set_get(self) -> None:
        self.assertEqual(send_command(self.host, self.port, "SET cli hello"), "+OK")
        self.assertEqual(send_command(self.host, self.port, "GET cli"), "$hello")
