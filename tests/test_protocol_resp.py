from __future__ import annotations

import io
import socket

from mini_redis.protocol import parse_resp
from tests.support import MiniRedisTCPTestCase


def build_resp_command(*parts: str) -> bytes:
    chunks = [f"*{len(parts)}\r\n".encode("ascii")]
    for part in parts:
        payload = part.encode("utf-8")
        chunks.append(f"${len(payload)}\r\n".encode("ascii"))
        chunks.append(payload + b"\r\n")
    return b"".join(chunks)


class MiniRedisRespTests(MiniRedisTCPTestCase):
    def test_parse_resp_parses_bulk_string_array(self) -> None:
        payload = io.BytesIO(b"$3\r\nSET\r\n$5\r\nhello\r\n$5\r\nworld\r\n")
        self.assertEqual(parse_resp(b"*3\r\n", payload), ["SET", "hello", "world"])

    def test_resp_set_get_del_round_trip(self) -> None:
        with socket.create_connection((self.host, self.port), timeout=2) as client:
            file = client.makefile("rb")
            client.sendall(build_resp_command("SET", "resp:key", "resp-value"))
            self.assertEqual(file.readline(), b"+OK\r\n")

            client.sendall(build_resp_command("GET", "resp:key"))
            self.assertEqual(file.readline(), b"$10\r\n")
            self.assertEqual(file.readline(), b"resp-value\r\n")

            client.sendall(build_resp_command("DEL", "resp:key"))
            self.assertEqual(file.readline(), b":1\r\n")

            client.sendall(build_resp_command("GET", "resp:key"))
            self.assertEqual(file.readline(), b"$-1\r\n")

    def test_resp_set_nx_and_invalid_modifier(self) -> None:
        with socket.create_connection((self.host, self.port), timeout=2) as client:
            file = client.makefile("rb")
            client.sendall(build_resp_command("SET", "seat-lock", "user-a", "NX"))
            self.assertEqual(file.readline(), b"+OK\r\n")

            client.sendall(build_resp_command("SET", "seat-lock", "user-b", "NX"))
            self.assertEqual(file.readline(), b"$-1\r\n")

            client.sendall(build_resp_command("SET", "seat-lock", "user-c", "XX"))
            self.assertEqual(file.readline(), b"-ERR only NX modifier is supported\r\n")

    def test_resp_multiple_requests_on_same_connection(self) -> None:
        with socket.create_connection((self.host, self.port), timeout=2) as client:
            file = client.makefile("rb")
            client.sendall(build_resp_command("PING"))
            self.assertEqual(file.readline(), b"+PONG\r\n")
            client.sendall(build_resp_command("PING"))
            self.assertEqual(file.readline(), b"+PONG\r\n")

    def test_resp_reports_parse_errors(self) -> None:
        with socket.create_connection((self.host, self.port), timeout=2) as client:
            file = client.makefile("rb")
            client.sendall(b"*1\r\n+PING\r\n")
            self.assertEqual(file.readline(), b"-ERR only RESP bulk strings are supported\r\n")
