"""
Mini Redis raw CLI and ticketing web bridge.

Default mode starts a local web server that serves a responsive ticketing dashboard.
The dashboard talks to the Mini Redis TCP server through RESP commands.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import random
import shlex
import socket
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6380
WEB_HOST = "127.0.0.1"
WEB_PORT = 8000
WEB_ROOT = Path(__file__).with_name("webapp")


@dataclass
class RespResult:
    kind: str
    value: str | int | None
    raw_preview: bytes


def default_seats() -> list[str]:
    layout = {
        "1F": {
            "A": list(range(1, 10)) + list(range(11, 19)) + list(range(20, 28)),
            "B": list(range(1, 10)) + list(range(11, 19)) + list(range(20, 28)),
            "C": list(range(1, 10)) + list(range(11, 20)) + list(range(21, 29)),
            "D": list(range(1, 9)) + list(range(10, 20)) + list(range(21, 30)),
            "E": list(range(1, 9)) + list(range(10, 20)) + list(range(21, 30)),
            "F": list(range(1, 8)) + list(range(9, 19)) + list(range(20, 30)),
            "G": list(range(1, 8)) + list(range(9, 19)) + list(range(20, 29)),
            "H": list(range(1, 7)) + list(range(8, 19)) + list(range(20, 29)),
            "J": list(range(1, 6)) + list(range(7, 18)) + list(range(19, 29)),
            "K": list(range(1, 6)) + list(range(7, 18)) + list(range(19, 28)),
            "L": list(range(1, 5)) + list(range(6, 18)) + list(range(19, 26)),
        },
        "2F": {
            "A": list(range(1, 6)) + list(range(7, 16)) + list(range(17, 25)),
            "B": list(range(1, 7)) + list(range(8, 17)) + list(range(18, 28)),
            "C": list(range(1, 6)) + list(range(7, 17)) + list(range(18, 28)),
            "D": list(range(1, 6)) + list(range(7, 17)) + list(range(18, 27)),
            "E": list(range(2, 6)) + list(range(7, 18)) + list(range(20, 27)),
            "F": list(range(1, 7)) + list(range(8, 21)) + list(range(22, 28)),
        },
    }

    seats: list[str] = []
    for section, rows in layout.items():
        for row, numbers in rows.items():
            for number in numbers:
                seats.append(f"{section}-{row}{number:02d}")
    return seats


def build_request(tokens: list[str]) -> bytes:
    parts = [f"*{len(tokens)}\r\n".encode()]
    for token in tokens:
        encoded = token.encode()
        parts.append(f"${len(encoded)}\r\n".encode())
        parts.append(encoded + b"\r\n")
    return b"".join(parts)


def read_line(sock: socket.socket) -> bytes:
    data = b""
    while not data.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("server closed the connection")
        data += chunk
    return data[:-2]


def read_response(sock: socket.socket) -> RespResult:
    prefix = sock.recv(1)
    if not prefix:
        raise ConnectionError("server closed the connection")

    if prefix == b"+":
        value = read_line(sock).decode()
        return RespResult("simple", value, prefix + value.encode() + b"\r\n")

    if prefix == b"-":
        value = read_line(sock).decode()
        return RespResult("error", value, prefix + value.encode() + b"\r\n")

    if prefix == b":":
        value = int(read_line(sock).decode())
        return RespResult("integer", value, prefix + str(value).encode() + b"\r\n")

    if prefix == b"$":
        length = int(read_line(sock).decode())
        if length == -1:
            return RespResult("nil", None, b"$-1\r\n")
        data = b""
        while len(data) < length + 2:
            chunk = sock.recv(length + 2 - len(data))
            if not chunk:
                raise ConnectionError("server closed the connection")
            data += chunk
        text = data[:-2].decode()
        return RespResult("bulk", text, prefix + str(length).encode() + b"\r\n" + data)

    raise ValueError(f"unsupported RESP prefix: {prefix!r}")


def send_tokens(sock: socket.socket, tokens: list[str]) -> tuple[bytes, RespResult]:
    request = build_request(tokens)
    sock.sendall(request)
    return request, read_response(sock)


def send_command(sock: socket.socket, raw: str) -> tuple[bytes, RespResult]:
    return send_tokens(sock, shlex.split(raw))


def request_tokens(tokens: list[str]) -> RespResult:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((REDIS_HOST, REDIS_PORT))
        _, response = send_tokens(sock, tokens)
        return response


def request_json(tokens: list[str]) -> dict:
    result = request_tokens(tokens)
    if result.kind == "error":
        raise ValueError(str(result.value))
    if result.kind != "bulk" or result.value is None:
        raise ValueError(f"expected bulk json response, got {result.kind}")
    return json.loads(str(result.value))


def format_result(result: RespResult) -> str:
    if result.kind == "simple":
        return f"simple string: {result.value}"
    if result.kind == "error":
        return f"error: {result.value}"
    if result.kind == "integer":
        return f"integer: {result.value}"
    if result.kind == "nil":
        return "nil"
    return f"bulk string: {result.value}"


def ensure_event(event_id: str) -> dict:
    try:
        state = request_json(["TICKET_STATE", event_id])
        if state.get("ok"):
            return state
    except Exception:
        pass
    return request_json(["TICKET_INIT", event_id, "2", "20", *default_seats()])


def simulate_ticketing(event_id: str, total_users: int, scenario: str, selected_seat: str | None) -> dict:
    state = ensure_event(event_id)
    seat_ids = [seat["seat_id"] for seat in state["seats"]]

    counters = {"entered": 0, "confirmed": 0, "hold_fail": 0, "cancelled": 0, "timed_out": 0}
    counters_lock = threading.Lock()

    def choose_seat() -> str:
        if scenario == "same-seat":
            return selected_seat or seat_ids[0]
        return random.choice(seat_ids)

    def worker(index: int) -> None:
        user_id = f"sim-{index:03d}"
        try:
            status = request_json(["TICKET_ENTER", event_id, user_id])
            with counters_lock:
                counters["entered"] += 1
            deadline = time.time() + 12

            while status.get("status") == "WAITING" and time.time() < deadline:
                time.sleep(0.2)
                status = request_json(["TICKET_STATUS", event_id, user_id])

            if status.get("status") != "ADMITTED":
                if status.get("status") == "WAITING":
                    request_json(["TICKET_EXIT", event_id, user_id])
                    with counters_lock:
                        counters["timed_out"] += 1
                return

            seat_id = choose_seat()
            hold_result = request_json(["TICKET_HOLD", event_id, user_id, seat_id])
            if not hold_result.get("ok"):
                request_json(["TICKET_EXIT", event_id, user_id])
                with counters_lock:
                    counters["hold_fail"] += 1
                return

            time.sleep(random.uniform(0.05, 0.25))
            if scenario == "queue-rush" and index % 5 == 0:
                request_json(["TICKET_CANCEL", event_id, user_id])
                with counters_lock:
                    counters["cancelled"] += 1
                return

            confirm_result = request_json(["TICKET_CONFIRM", event_id, user_id])
            if confirm_result.get("ok"):
                with counters_lock:
                    counters["confirmed"] += 1
            else:
                with counters_lock:
                    counters["hold_fail"] += 1
        except Exception:
            with counters_lock:
                counters["hold_fail"] += 1

    threads = []
    for index in range(total_users):
        worker_thread = threading.Thread(target=worker, args=(index,), daemon=True)
        threads.append(worker_thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    final_state = request_json(["TICKET_STATE", event_id])
    return {
        "scenario": scenario,
        "users": total_users,
        "entered": counters["entered"],
        "confirmed": counters["confirmed"],
        "hold_fail": counters["hold_fail"],
        "cancelled": counters["cancelled"],
        "timed_out": counters["timed_out"],
        "final_state": final_state,
    }


class TicketingBridgeHandler(BaseHTTPRequestHandler):
    server_version = "MiniRedisTicketingBridge/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            event_id = parse_qs(parsed.query).get("event_id", ["concert-demo"])[0]
            self.respond_json(HTTPStatus.OK, ensure_event(event_id))
            return

        if parsed.path == "/api/health":
            self.respond_json(HTTPStatus.OK, {"ok": True, "redis_host": REDIS_HOST, "redis_port": REDIS_PORT})
            return

        self.serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self.read_json()

        try:
            if parsed.path == "/api/init":
                event_id = body.get("eventId", "concert-demo")
                active_limit = str(body.get("activeLimit", 2))
                hold_ttl = str(body.get("holdTtl", 20))
                seats = [seat.strip() for seat in body.get("seatsCsv", "").split(",") if seat.strip()]
                if not seats:
                    seats = default_seats()
                payload = request_json(["TICKET_INIT", event_id, active_limit, hold_ttl, *seats])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/reset":
                payload = request_json(["TICKET_RESET", body["eventId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/enter":
                payload = request_json(["TICKET_ENTER", body["eventId"], body["userId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/status":
                payload = request_json(["TICKET_STATUS", body["eventId"], body["userId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/hold":
                payload = request_json(["TICKET_HOLD", body["eventId"], body["userId"], body["seatId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/confirm":
                payload = request_json(["TICKET_CONFIRM", body["eventId"], body["userId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/cancel":
                payload = request_json(["TICKET_CANCEL", body["eventId"], body["userId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/exit":
                payload = request_json(["TICKET_EXIT", body["eventId"], body["userId"]])
                self.respond_json(HTTPStatus.OK, payload)
                return

            if parsed.path == "/api/simulate":
                payload = simulate_ticketing(
                    body.get("eventId", "concert-demo"),
                    int(body.get("users", 20)),
                    body.get("scenario", "same-seat"),
                    body.get("selectedSeat"),
                )
                self.respond_json(HTTPStatus.OK, payload)
                return

        except KeyError as exc:
            self.respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "reason": f"missing field {exc}"})
            return
        except ValueError as exc:
            self.respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "reason": str(exc)})
            return
        except ConnectionError as exc:
            self.respond_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "reason": str(exc)})
            return

        self.respond_json(HTTPStatus.NOT_FOUND, {"ok": False, "reason": "route not found"})

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def respond_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        file_path = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in file_path.parents and file_path != WEB_ROOT.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_web_server(host: str, port: int) -> None:
    ensure_event("concert-demo")
    httpd = ThreadingHTTPServer((host, port), TicketingBridgeHandler)
    print(f"Ticketing web app on http://{host}:{port}")
    print(f"Bridge target Mini Redis: {REDIS_HOST}:{REDIS_PORT}")
    httpd.serve_forever()


def run_cli() -> None:
    print(f"Connect to {REDIS_HOST}:{REDIS_PORT}")
    print("Enter raw commands like: PING, SET a 10, TICKET_STATE concert-demo")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((REDIS_HOST, REDIS_PORT))
        while True:
            raw = input("redis> ").strip()
            if not raw:
                continue
            if raw.lower() in {"quit", "exit"}:
                print("bye")
                break
            try:
                request, result = send_command(sock, raw)
            except (ConnectionError, ValueError) as exc:
                print(f"response error: {exc}")
                continue
            print(f"RESP request bytes: {request!r}")
            print(f"server -> {format_result(result)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mini Redis ticketing bridge")
    parser.add_argument("--cli", action="store_true", help="open the raw RESP CLI instead of the web app")
    parser.add_argument("--redis-host", default=REDIS_HOST)
    parser.add_argument("--redis-port", type=int, default=REDIS_PORT)
    parser.add_argument("--host", default=WEB_HOST)
    parser.add_argument("--port", type=int, default=WEB_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global REDIS_HOST, REDIS_PORT
    REDIS_HOST = args.redis_host
    REDIS_PORT = args.redis_port
    if args.cli:
        run_cli()
        return
    run_web_server(args.host, args.port)


if __name__ == "__main__":
    main()
