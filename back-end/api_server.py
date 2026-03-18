import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
API_HOST = "0.0.0.0"
API_PORT = 8000

SHOW_INFO = {
    "id": "show-2026-midnight-signal",
    "title": "Midnight Signal Tour",
    "description": "A one-night performance mixing neon city atmosphere, heavy drums, and live visual staging.",
    "venue": "Jungle Arena",
    "date": "2026-04-08 19:30",
}

SEAT_ROWS = ("A", "B", "C", "D", "E", "F")
SEATS_PER_ROW = 8


def seat_ids():
    seats = []
    for row in SEAT_ROWS:
        for number in range(1, SEATS_PER_ROW + 1):
            seats.append(f"{row}-{number:02d}")
    return seats


ALL_SEAT_IDS = seat_ids()


def redis_command(command):
    with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=2.0) as sock:
        sock.settimeout(0.3)
        sock.sendall((command.strip() + "\n").encode("utf-8"))

        chunks = []
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                break

            if not data:
                break

            chunks.append(data)
            if len(data) < 4096:
                break

    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def parse_list_response(raw_text):
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    if raw_text.startswith("[") and raw_text.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(raw_text)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, SyntaxError):
            pass

    return []


def status_key(seat_id):
    return f"ticket:seat:{seat_id}:status"


def owner_key(seat_id):
    return f"ticket:seat:{seat_id}:owner"


def ensure_seed_data():
    for seat_id in ALL_SEAT_IDS:
        redis_command(f"SETNX {status_key(seat_id)} available")


def load_seats():
    ensure_seed_data()
    status_keys = [status_key(seat_id) for seat_id in ALL_SEAT_IDS]
    owner_keys = [owner_key(seat_id) for seat_id in ALL_SEAT_IDS]
    raw_status_values = redis_command("MGET " + " ".join(status_keys))
    raw_owner_values = redis_command("MGET " + " ".join(owner_keys))
    status_values = parse_list_response(raw_status_values)
    owner_values = parse_list_response(raw_owner_values)
    seats = []

    for index, seat_id in enumerate(ALL_SEAT_IDS):
        status = status_values[index] if index < len(status_values) else "(nil)"
        owner = owner_values[index] if index < len(owner_values) else "(nil)"
        if status == "(nil)":
            status = "available"
        if owner == "(nil)":
            owner = None
        seats.append(
            {
                "id": seat_id,
                "status": status,
                "owner": owner,
            }
        )
    return seats


def summarize_seats(seats):
    total = len(seats)
    remaining = sum(1 for seat in seats if seat["status"] == "available")
    booked = sum(1 for seat in seats if seat["status"] == "booked")
    held = sum(1 for seat in seats if seat["status"] == "held")
    return {
        "total": total,
        "remaining": remaining,
        "booked": booked,
        "held": held,
    }


def status_payload():
    seats = load_seats()
    return {
        "show": SHOW_INFO,
        "seats": seats,
        "summary": summarize_seats(seats),
    }


def current_status(seat_id):
    raw = redis_command(f"GET {status_key(seat_id)}")
    return "available" if raw == "(nil)" else raw


def set_seat_status(seat_id, new_status, actor):
    redis_command(f"SET {status_key(seat_id)} {new_status}")
    redis_command(f"SET {owner_key(seat_id)} {actor}")


def clear_seat_owner(seat_id):
    redis_command(f"DEL {owner_key(seat_id)}")


def book_seat(seat_id, actor):
    if seat_id not in ALL_SEAT_IDS:
        return {"ok": False, "message": "Unknown seat id."}, 404

    ensure_seed_data()
    status = current_status(seat_id)
    if status != "available":
        return {
            "ok": False,
            "message": f"{seat_id} is not available.",
            "seat": {"id": seat_id, "status": status},
        }, 409

    set_seat_status(seat_id, "booked", actor)
    return {
        "ok": True,
        "message": f"{seat_id} booked successfully.",
        "seat": {"id": seat_id, "status": "booked"},
        "state": status_payload(),
    }, 200


def cancel_seat(seat_id, actor):
    if seat_id not in ALL_SEAT_IDS:
        return {"ok": False, "message": "Unknown seat id."}, 404

    ensure_seed_data()
    status = current_status(seat_id)
    if status != "booked":
        return {
            "ok": False,
            "message": f"{seat_id} is not booked, so it cannot be canceled.",
            "seat": {"id": seat_id, "status": status},
        }, 409

    redis_command(f"SET {status_key(seat_id)} available")
    if actor:
        redis_command(f"SET {owner_key(seat_id)} {actor}")
    else:
        clear_seat_owner(seat_id)
    return {
        "ok": True,
        "message": f"{seat_id} cancellation completed.",
        "seat": {"id": seat_id, "status": "available"},
        "state": status_payload(),
    }, 200


def pick_simulation_seat(strategy, wants_cancel):
    seats = load_seats()
    if wants_cancel:
        candidates = [seat for seat in seats if seat["status"] == "booked"]
    else:
        candidates = [seat for seat in seats if seat["status"] == "available"]

    if not candidates:
        return None

    if strategy == "front":
        return candidates[0]["id"]
    if strategy == "back":
        return candidates[-1]["id"]

    import random
    return random.choice(candidates)["id"]


def simulation_step(strategy, wants_cancel, actor):
    seat_id = pick_simulation_seat(strategy, wants_cancel)
    if not seat_id:
        return {
            "ok": False,
            "message": "No seat is available for this simulation step.",
            "state": status_payload(),
        }, 409

    if wants_cancel:
        payload, code = cancel_seat(seat_id, actor)
        if payload["ok"]:
            payload["message"] = f"Simulation canceled {seat_id}."
        return payload, code

    payload, code = book_seat(seat_id, actor)
    if payload["ok"]:
        payload["message"] = f"Simulation booked {seat_id}."
    return payload, code


class ApiHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            return self._send_json(200, {"ok": True, "message": "API server is running."})

        if parsed.path == "/api/status":
            try:
                payload = status_payload()
                return self._send_json(200, payload)
            except OSError as exc:
                return self._send_json(502, {"ok": False, "message": f"Socket bridge failed: {exc}"})

        return self._send_json(404, {"ok": False, "message": "Route not found."})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            body = self._read_json_body()
        except ValueError as exc:
            return self._send_json(400, {"ok": False, "message": str(exc)})

        try:
            if parsed.path == "/api/book":
                seat_id = body.get("seatId", "").strip()
                actor = body.get("actor", "manual")
                payload, status_code = book_seat(seat_id, actor)
                return self._send_json(status_code, payload)

            if parsed.path == "/api/cancel":
                seat_id = body.get("seatId", "").strip()
                actor = body.get("actor", "manual")
                payload, status_code = cancel_seat(seat_id, actor)
                return self._send_json(status_code, payload)

            if parsed.path == "/api/simulate-step":
                strategy = body.get("strategy", "random")
                wants_cancel = bool(body.get("cancel", False))
                actor = body.get("actor", "simulator")
                payload, status_code = simulation_step(strategy, wants_cancel, actor)
                return self._send_json(status_code, payload)
        except OSError as exc:
            return self._send_json(502, {"ok": False, "message": f"Socket bridge failed: {exc}"})

        return self._send_json(404, {"ok": False, "message": "Route not found."})

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def _send_json(self, status_code, payload):
        encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format_string, *args):
        print(f"api {self.address_string()} - {format_string % args}")


def main():
    server = ThreadingHTTPServer((API_HOST, API_PORT), ApiHandler)
    print(f"api server is listening on {API_HOST}:{API_PORT}")
    print(f"bridging requests to socket server at {REDIS_HOST}:{REDIS_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
