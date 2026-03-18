from __future__ import annotations

import http.client
import json
import threading
import unittest

from mini_redis.server import MiniRedisHandler, MiniRedisTCPServer
from mini_redis.store import MiniRedisStore
from ticketing_service.server import TicketingHTTPServer, TicketingHandler
from ticketing_service.service import TicketingConfig, TicketingService


class TicketingServiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.redis_server = MiniRedisTCPServer(
            ("127.0.0.1", 0),
            MiniRedisHandler,
            store=MiniRedisStore(),
            sweep_interval=0.1,
        )
        self.redis_thread = threading.Thread(target=self.redis_server.serve_forever, daemon=True)
        self.redis_thread.start()
        self.redis_host, self.redis_port = self.redis_server.server_address

        service = TicketingService(
            self.redis_host,
            self.redis_port,
            config=TicketingConfig(
                event_id="test-show",
                max_active_users=1,
                hold_seconds=30,
                seat_ids=("A1", "A2"),
            ),
        )
        service.bootstrap()
        self.http_server = TicketingHTTPServer(("127.0.0.1", 0), TicketingHandler, service)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()
        self.http_host, self.http_port = self.http_server.server_address
        self.post("/api/reset", {})

    def tearDown(self) -> None:
        self.http_server.shutdown()
        self.http_server.server_close()
        self.http_thread.join(timeout=1)

        self.redis_server.shutdown()
        self.redis_server.server_close()
        self.redis_thread.join(timeout=1)

    def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        conn = http.client.HTTPConnection(self.http_host, self.http_port, timeout=5)
        body = json.dumps(payload)
        conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8")
        conn.close()
        return json.loads(raw_body)

    def get(self, path: str) -> dict[str, object]:
        conn = http.client.HTTPConnection(self.http_host, self.http_port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8")
        conn.close()
        return json.loads(raw_body)

    def get_html(self, path: str) -> str:
        conn = http.client.HTTPConnection(self.http_host, self.http_port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        raw_body = response.read().decode("utf-8")
        conn.close()
        return raw_body

    def test_a_b_page_routes_are_exposed(self) -> None:
        entry_page = self.get_html("/")
        waiting_page = self.get_html("/waiting-room?user_id=user-b")
        ticketing_page = self.get_html("/ticketing?user_id=user-a")
        ops_page = self.get_html("/ops")

        self.assertIn("예매 시작 페이지", entry_page)
        self.assertIn("Page B Waiting Room", waiting_page)
        self.assertIn("Page A Ticketing Room", ticketing_page)
        self.assertIn("Operator View", ops_page)

    def test_second_user_goes_to_waiting_room_when_capacity_is_full(self) -> None:
        first = self.post("/api/enter", {"user_id": "user-a"})
        second = self.post("/api/enter", {"user_id": "user-b"})

        self.assertEqual(first["status"], "admitted")
        self.assertEqual(second["status"], "waiting")
        self.assertEqual(second["queue_position"], 1)

    def test_state_exposes_current_admitted_user_for_waiting_room_checks(self) -> None:
        self.post("/api/enter", {"user_id": "user-a"})
        self.post("/api/enter", {"user_id": "user-b"})

        state = self.get("/api/state")

        self.assertEqual(state["admitted_users"], ["user-a"])
        self.assertEqual(state["waiting_users"], ["user-b"])

    def test_confirm_promotes_next_waiting_user(self) -> None:
        self.post("/api/enter", {"user_id": "user-a"})
        self.post("/api/enter", {"user_id": "user-b"})
        reserve = self.post("/api/reserve", {"user_id": "user-a", "seat_id": "A1"})
        confirm = self.post("/api/confirm", {"user_id": "user-a"})
        waiting_status = self.get("/api/status?user_id=user-b")

        self.assertEqual(reserve["status"], "holding")
        self.assertEqual(confirm["status"], "confirmed")
        self.assertEqual(confirm["promoted"], ["user-b"])
        self.assertEqual(waiting_status["status"], "admitted")

    def test_same_seat_cannot_be_reserved_twice(self) -> None:
        self.http_server.service.config = TicketingConfig(
            event_id="test-show",
            max_active_users=2,
            hold_seconds=30,
            seat_ids=("A1", "A2"),
        )
        self.post("/api/reset", {})

        self.post("/api/enter", {"user_id": "user-a"})
        self.post("/api/enter", {"user_id": "user-b"})
        first_reserve = self.post("/api/reserve", {"user_id": "user-a", "seat_id": "A1"})
        second_reserve = self.post("/api/reserve", {"user_id": "user-b", "seat_id": "A1"})

        self.assertEqual(first_reserve["status"], "holding")
        self.assertEqual(second_reserve["status"], "error")
        self.assertEqual(second_reserve["reason"], "seat_taken")
