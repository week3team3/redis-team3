"""
RESP mini Redis server for learning.

Why this file exists:
- parse_resp()      : input parsing layer
- handle_command()  : command processing layer
- build_resp_response() : output response layer
- store(dict)       : in-memory state storage

RESP quick examples:
- SET a 10
  *3\r\n$3\r\nSET\r\n$1\r\na\r\n$2\r\n10\r\n
- GET a
  *2\r\n$3\r\nGET\r\n$1\r\na\r\n
- CLAIM stock
  *2\r\n$5\r\nCLAIM\r\n$5\r\nstock\r\n

RESP response examples:
- +OK\r\n                  -> simple string
- $2\r\n10\r\n            -> bulk string
- $-1\r\n                 -> nil
- :1\r\n                  -> integer
- -ERR wrong args\r\n     -> error

Learning checkpoints:
1. Send one RESP request from client.py
2. Check parse_resp() debug output on the server
3. Verify SET / GET / DEL
4. Compare simple string, bulk string, nil, integer, error responses
5. Send many requests on one connection
6. Send invalid input and observe RESP error
7. Restart server and confirm data disappears
8. Connect two clients and confirm shared dict state
9. Test INCR / DECR
10. Test SET key value NX
11. Test CLAIM stock for coupon-like stock control
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Optional


HOST = "127.0.0.1"
PORT = 6380
store: dict[str, str] = {}  # 인메모리 상태 저장소
expires_at: dict[str, float] = {}
store_lock = threading.Lock()


def purge_expired_key(key: str) -> None:
    """Delete a key if its TTL has already passed."""

    expire_time = expires_at.get(key)
    if expire_time is None:
        return
    if time.time() < expire_time:
        return
    store.pop(key, None)
    expires_at.pop(key, None)


def read_ttl_seconds(key: str) -> int:
    """Return Redis-like TTL values: -2 missing, -1 no expiry, otherwise remaining seconds."""

    purge_expired_key(key)
    if key not in store:
        return -2
    expire_time = expires_at.get(key)
    if expire_time is None:
        return -1
    remaining = int(expire_time - time.time())
    return max(remaining, 0)


def parse_resp(buffer: bytes) -> tuple[Optional[list[str]], int]:
    """
    Parse one RESP array command from the current buffer.

    Returns:
    - (tokens, consumed_bytes) when one full command is available
    - (None, 0) when more data is needed

    Supported request shape for this learning server:
    *<count>\r\n$<len>\r\n<arg>\r\n...
    """

    if not buffer:
        return None, 0

    if buffer[:1] != b"*":
        raise ValueError("expected RESP array request")

    first_line_end = buffer.find(b"\r\n")
    if first_line_end == -1:
        return None, 0

    try:
        arg_count = int(buffer[1:first_line_end].decode())
    except ValueError as exc:
        raise ValueError("invalid array length") from exc

    index = first_line_end + 2
    tokens: list[str] = []

    for _ in range(arg_count):
        if index >= len(buffer):
            return None, 0

        if buffer[index:index + 1] != b"$":
            raise ValueError("expected bulk string")

        bulk_len_end = buffer.find(b"\r\n", index)
        if bulk_len_end == -1:
            return None, 0

        try:
            bulk_len = int(buffer[index + 1:bulk_len_end].decode())
        except ValueError as exc:
            raise ValueError("invalid bulk string length") from exc

        if bulk_len < 0:
            raise ValueError("negative bulk string length is not allowed in requests")

        value_start = bulk_len_end + 2
        value_end = value_start + bulk_len

        if value_end + 2 > len(buffer):
            return None, 0

        if buffer[value_end:value_end + 2] != b"\r\n":
            raise ValueError("bulk string missing CRLF terminator")

        tokens.append(buffer[value_start:value_end].decode())
        index = value_end + 2

    return tokens, index

# 명령 처리부
def handle_command(tokens: list[str]) -> tuple[str, str | int | None]:
    """
    Execute one command against the in-memory dict store.

    Response tuple kinds:
    - simple  : +OK
    - bulk    : $<len>... or nil when value is None
    - integer : :1
    - error   : -ERR ...
    """

    if not tokens:
        return "error", "empty command"

    command = tokens[0].upper()

    if command == "SET":
        if len(tokens) == 3:
            key, value = tokens[1], tokens[2]
            with store_lock:
                purge_expired_key(key)
                store[key] = value
                expires_at.pop(key, None)
            return "simple", "OK"

        if len(tokens) == 4 and tokens[3].upper() == "NX":
            key, value = tokens[1], tokens[2]
            with store_lock:
                purge_expired_key(key)
                if key in store:
                    return "bulk", None
                store[key] = value
                expires_at.pop(key, None)
            return "simple", "OK"

        return "error", "wrong number of arguments for SET"

    if command == "GET":
        if len(tokens) != 2:
            return "error", "wrong number of arguments for GET"
        key = tokens[1]
        with store_lock:
            purge_expired_key(key)
            return "bulk", store.get(key)

    if command == "DEL":
        if len(tokens) != 2:
            return "error", "wrong number of arguments for DEL"
        key = tokens[1]
        with store_lock:
            purge_expired_key(key)
            deleted = 1 if key in store else 0
            store.pop(key, None)
            expires_at.pop(key, None)
            return "integer", deleted

    if command == "EXISTS":
        if len(tokens) != 2:
            return "error", "wrong number of arguments for EXISTS"
        key = tokens[1]
        with store_lock:
            purge_expired_key(key)
            return "integer", 1 if key in store else 0

    if command in {"INCR", "DECR"}:
        if len(tokens) != 2:
            return "error", f"wrong number of arguments for {command}"

        key = tokens[1]
        with store_lock:
            purge_expired_key(key)
            raw_value = store.get(key, "0")

            try:
                current = int(raw_value)
            except ValueError:
                return "error", "value is not an integer"

            next_value = current + 1 if command == "INCR" else current - 1
            store[key] = str(next_value)
            return "integer", next_value

    if command == "CLAIM":
        if len(tokens) != 2:
            return "error", "wrong number of arguments for CLAIM"

        key = tokens[1]
        with store_lock:
            purge_expired_key(key)
            raw_value = store.get(key, "0")

            try:
                current = int(raw_value)
            except ValueError:
                return "error", "value is not an integer"

            if current <= 0:
                return "error", "sold out"

            next_value = current - 1
            store[key] = str(next_value)
            return "integer", next_value

    if command == "EXPIRE":
        if len(tokens) != 3:
            return "error", "wrong number of arguments for EXPIRE"

        key = tokens[1]
        try:
            seconds = int(tokens[2])
        except ValueError:
            return "error", "TTL must be an integer"

        if seconds < 0:
            return "error", "TTL must be zero or positive"

        with store_lock:
            purge_expired_key(key)
            if key not in store:
                return "integer", 0
            expires_at[key] = time.time() + seconds
            return "integer", 1

    if command == "TTL":
        if len(tokens) != 2:
            return "error", "wrong number of arguments for TTL"

        key = tokens[1]
        with store_lock:
            return "integer", read_ttl_seconds(key)

    return "error", f"unknown command '{tokens[0]}'"

# 출력 응답부
def build_resp_response(kind: str, value: str | int | None) -> bytes:
    """Convert an internal response tuple into RESP bytes."""

    if kind == "simple":
        return f"+{value}\r\n".encode()

    if kind == "bulk":
        if value is None:
            return b"$-1\r\n"
        text = str(value)
        return f"${len(text)}\r\n{text}\r\n".encode()

    if kind == "integer":
        return f":{value}\r\n".encode()

    if kind == "error":
        return f"-ERR {value}\r\n".encode()

    return b"-ERR internal server error\r\n"


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    """
    Process many RESP requests on one TCP connection.

    One connection can keep sending:
    SET a 10
    GET a
    INCR a
    ...
    """

    print(f"[CONNECT] {addr}")
    buffer = b""

    with conn:
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    print(f"[DISCONNECT] {addr}")
                    break

                buffer += chunk

                while buffer:
                    try:
                        #입력 파싱부
                        tokens, consumed = parse_resp(buffer)
                    except ValueError as exc:
                        response = build_resp_response("error", str(exc))
                        conn.sendall(response)
                        print(f"[PARSE ERROR] {addr} -> {exc}")
                        buffer = b""
                        break

                    if tokens is None:
                        break

                    print(f"[PARSED] {addr} -> {tokens}")
                    kind, value = handle_command(tokens)
                    response = build_resp_response(kind, value)
                    conn.sendall(response)
                    print(f"[RESPONSE] {addr} -> {response!r}")
                    buffer = buffer[consumed:]

            except ConnectionResetError:
                print(f"[RESET] {addr}")
                break


def run_server() -> None:
    print(f"Mini RESP Redis server listening on {HOST}:{PORT}")
    print("State store is a plain Python dict. Restart the server to reset all data.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()


if __name__ == "__main__":
    run_server()
