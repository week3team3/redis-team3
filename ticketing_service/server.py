from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from ticketing_service.pages import (
    render_entry_page,
    render_ops_page,
    render_ticketing_page,
    render_waiting_room_page,
)
from ticketing_service.service import TicketingConfig, TicketingService


class TicketingHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], service: TicketingService):
        super().__init__(server_address, handler_cls)
        self.service = service


class TicketingHandler(BaseHTTPRequestHandler):
    server: TicketingHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        user_id = parse_qs(parsed.query).get("user_id", [""])[0]

        if parsed.path == "/":
            self._write_html(render_entry_page(self.server.service.config))
            return
        if parsed.path == "/waiting-room":
            self._write_html(render_waiting_room_page(user_id))
            return
        if parsed.path == "/ticketing":
            self._write_html(render_ticketing_page(user_id, self.server.service.config.seat_ids))
            return
        if parsed.path == "/ops":
            self._write_html(render_ops_page(self.server.service.config))
            return
        if parsed.path == "/api/state":
            self._write_json(HTTPStatus.OK, self.server.service.state())
            return
        if parsed.path == "/api/status":
            self._write_json(HTTPStatus.OK, self.server.service.status(user_id))
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()

        if parsed.path == "/api/enter":
            self._write_json(HTTPStatus.OK, self.server.service.enter(payload["user_id"]))
            return
        if parsed.path == "/api/advance":
            count = int(payload.get("count", 1))
            self._write_json(HTTPStatus.OK, self.server.service.advance_queue(count))
            return
        if parsed.path == "/api/reserve":
            self._write_json(
                HTTPStatus.OK,
                self.server.service.reserve(payload["user_id"], payload["seat_id"]),
            )
            return
        if parsed.path == "/api/confirm":
            self._write_json(HTTPStatus.OK, self.server.service.confirm(payload["user_id"]))
            return
        if parsed.path == "/api/cancel":
            self._write_json(HTTPStatus.OK, self.server.service.cancel(payload["user_id"]))
            return
        if parsed.path == "/api/reset":
            self._write_json(HTTPStatus.OK, self.server.service.reset())
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _write_html(self, html_body: str) -> None:
        encoded = html_body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ticketing demo service backed by PyMiniRedis.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--event-id", default="concert-demo")
    parser.add_argument("--max-active-users", type=int, default=2)
    parser.add_argument("--hold-seconds", type=int, default=300)
    parser.add_argument("--seat-ids", default="A1,A2,A3,A4")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = TicketingConfig(
        event_id=args.event_id,
        max_active_users=args.max_active_users,
        hold_seconds=args.hold_seconds,
        seat_ids=tuple(seat.strip() for seat in args.seat_ids.split(",") if seat.strip()),
    )
    service = TicketingService(args.redis_host, args.redis_port, config=config)
    service.bootstrap()
    with TicketingHTTPServer((args.host, args.port), TicketingHandler, service) as server:
        print(f"Ticketing demo listening on http://{args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
