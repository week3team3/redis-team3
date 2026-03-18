from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time

from ticketing_service.redis_client import MiniRedisClient, MiniRedisClientError, RateLimitReply


@dataclass(frozen=True)
class TicketingConfig:
    event_id: str = "concert-demo"
    max_active_users: int = 2
    hold_seconds: int = 300
    rate_limit: int = 5
    rate_window_seconds: int = 2
    seat_ids: tuple[str, ...] = ("A1", "A2", "A3", "A4")


class TicketingService:
    def __init__(self, redis_host: str, redis_port: int, config: TicketingConfig | None = None) -> None:
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.config = config or TicketingConfig()

    def bootstrap(self) -> None:
        with self._client() as client:
            client.set(self._stock_key(), str(len(self.config.seat_ids)), nx=True)
            client.set(self._active_count_key(), "0", nx=True)

    def reset(self) -> dict[str, object]:
        with self._client() as client:
            participants = client.smembers(self._participants_key())
            for user_id in participants:
                client.delete(self._queue_token_key(user_id))
                client.delete(self._admission_key(user_id))
                client.delete(self._reservation_key(user_id))
            for seat_id in self.config.seat_ids:
                client.delete(self._seat_holder_key(seat_id))
            client.delete(self._queue_key())
            client.delete(self._participants_key())
            client.set(self._stock_key(), str(len(self.config.seat_ids)))
            client.set(self._active_count_key(), "0")
        return self.state()

    def enter(self, user_id: str) -> dict[str, object]:
        with self._client() as client:
            self._bootstrap_with(client)
            rate = client.ratecheck(
                self._rate_key(user_id),
                self.config.rate_limit,
                self.config.rate_window_seconds,
            )
            if not rate.allowed:
                return {
                    "status": "blocked",
                    "reason": "rate_limited",
                    "remaining": rate.remaining,
                    "reset_in": rate.reset_in,
                }

            client.sadd(self._participants_key(), user_id)
            if client.get(self._admission_key(user_id)) == "admitted":
                return self._admitted_payload(client, user_id)

            current_rank = client.zrank(self._queue_key(), user_id)
            if current_rank >= 0:
                return self._waiting_payload(client, user_id, current_rank)

            token_created = client.set(self._queue_token_key(user_id), "issued", nx=True)
            if not token_created:
                return self.status(user_id)

            queue_size = client.zcard(self._queue_key())
            active_count = self._read_int(client.get(self._active_count_key()))
            if active_count < self.config.max_active_users and queue_size == 0:
                client.set(self._admission_key(user_id), "admitted")
                client.incr(self._active_count_key())
                return self._admitted_payload(client, user_id)

            client.zadd(self._queue_key(), time(), user_id)
            rank = client.zrank(self._queue_key(), user_id)
            return self._waiting_payload(client, user_id, rank)

    def status(self, user_id: str) -> dict[str, object]:
        with self._client() as client:
            self._bootstrap_with(client)
            if client.get(self._admission_key(user_id)) == "admitted":
                payload = self._admitted_payload(client, user_id)
            else:
                rank = client.zrank(self._queue_key(), user_id)
                if rank >= 0:
                    payload = self._waiting_payload(client, user_id, rank)
                else:
                    reservation = client.hgetall(self._reservation_key(user_id))
                    if reservation:
                        payload = {
                            "status": reservation.get("status", "reservation"),
                            "user_id": user_id,
                            "reservation": reservation,
                            "state": self._state_payload(client),
                        }
                    else:
                        payload = {"status": "not_found", "user_id": user_id, "state": self._state_payload(client)}

            return payload

    def advance_queue(self, count: int = 1) -> dict[str, object]:
        promoted: list[str] = []
        with self._client() as client:
            self._bootstrap_with(client)
            for _ in range(max(count, 0)):
                active_count = self._read_int(client.get(self._active_count_key()))
                if active_count >= self.config.max_active_users:
                    break
                popped = client.zpopmin(self._queue_key())
                if popped is None:
                    break
                user_id, _ = popped
                client.set(self._admission_key(user_id), "admitted")
                client.incr(self._active_count_key())
                promoted.append(user_id)
            return {"promoted": promoted, "state": self._state_payload(client)}

    def reserve(self, user_id: str, seat_id: str) -> dict[str, object]:
        if seat_id not in self.config.seat_ids:
            return {"status": "error", "reason": "unknown_seat", "seat_id": seat_id}

        lock_key = self._seat_lock_key(seat_id)
        with self._client() as client:
            self._bootstrap_with(client)
            if client.get(self._admission_key(user_id)) != "admitted":
                return {"status": "error", "reason": "not_admitted", "user_id": user_id}

            current_reservation = client.hgetall(self._reservation_key(user_id))
            if current_reservation:
                return {"status": "error", "reason": "already_reserved", "reservation": current_reservation}

            if not client.lock(lock_key, user_id, 10):
                return {"status": "error", "reason": "seat_locked", "seat_id": seat_id}

            try:
                stock = self._read_int(client.get(self._stock_key()))
                if stock <= 0:
                    return {"status": "error", "reason": "sold_out"}

                created = client.set(self._seat_holder_key(seat_id), user_id, nx=True)
                if not created:
                    return {"status": "error", "reason": "seat_taken", "seat_id": seat_id}

                reservation_key = self._reservation_key(user_id)
                client.hset(reservation_key, "user_id", user_id)
                client.hset(reservation_key, "seat_id", seat_id)
                client.hset(reservation_key, "status", "holding")
                client.hset(reservation_key, "event_id", self.config.event_id)
                client.expire(reservation_key, self.config.hold_seconds)
                remaining_stock = client.decr(self._stock_key())
                return {
                    "status": "holding",
                    "user_id": user_id,
                    "seat_id": seat_id,
                    "hold_seconds": self.config.hold_seconds,
                    "remaining_stock": remaining_stock,
                }
            finally:
                client.unlock(lock_key, user_id)

    def confirm(self, user_id: str) -> dict[str, object]:
        with self._client() as client:
            self._bootstrap_with(client)
            reservation = client.hgetall(self._reservation_key(user_id))
            if not reservation:
                return {"status": "error", "reason": "reservation_not_found", "user_id": user_id}

            client.hset(self._reservation_key(user_id), "status", "confirmed")
            promoted = self._release_admission_and_promote(client, user_id)
            reservation = client.hgetall(self._reservation_key(user_id))
            return {"status": "confirmed", "reservation": reservation, "promoted": promoted}

    def cancel(self, user_id: str) -> dict[str, object]:
        with self._client() as client:
            self._bootstrap_with(client)
            reservation = client.hgetall(self._reservation_key(user_id))
            if not reservation:
                return {"status": "error", "reason": "reservation_not_found", "user_id": user_id}

            seat_id = reservation.get("seat_id")
            if seat_id:
                client.delete(self._seat_holder_key(seat_id))
            client.delete(self._reservation_key(user_id))
            remaining_stock = client.incr(self._stock_key())
            promoted = self._release_admission_and_promote(client, user_id)
            return {
                "status": "cancelled",
                "user_id": user_id,
                "remaining_stock": remaining_stock,
                "promoted": promoted,
            }

    def state(self) -> dict[str, object]:
        with self._client() as client:
            self._bootstrap_with(client)
            return self._state_payload(client)

    def _release_admission_and_promote(self, client: MiniRedisClient, user_id: str) -> list[str]:
        promoted: list[str] = []
        if client.get(self._admission_key(user_id)) == "admitted":
            client.delete(self._admission_key(user_id))
            client.decr(self._active_count_key())
        client.delete(self._queue_token_key(user_id))

        active_count = self._read_int(client.get(self._active_count_key()))
        if active_count < self.config.max_active_users:
            popped = client.zpopmin(self._queue_key())
            if popped is not None:
                next_user, _ = popped
                client.set(self._admission_key(next_user), "admitted")
                client.incr(self._active_count_key())
                promoted.append(next_user)
        return promoted

    def _state_payload(self, client: MiniRedisClient) -> dict[str, object]:
        participants = sorted(client.smembers(self._participants_key()))
        seats = {seat_id: client.get(self._seat_holder_key(seat_id)) for seat_id in self.config.seat_ids}
        admitted_users = [user_id for user_id in participants if client.get(self._admission_key(user_id)) == "admitted"]
        waiting_users = client.zrange(self._queue_key(), 0, -1)
        reservations = {
            user_id: client.hgetall(self._reservation_key(user_id))
            for user_id in participants
            if client.hgetall(self._reservation_key(user_id))
        }
        return {
            "event_id": self.config.event_id,
            "max_active_users": self.config.max_active_users,
            "stock": self._read_int(client.get(self._stock_key())),
            "active_count": self._read_int(client.get(self._active_count_key())),
            "queue_size": client.zcard(self._queue_key()),
            "waiting_users": waiting_users,
            "admitted_users": admitted_users,
            "seats": seats,
            "reservations": reservations,
        }

    def _admitted_payload(self, client: MiniRedisClient, user_id: str) -> dict[str, object]:
        return {
            "status": "admitted",
            "user_id": user_id,
            "queue_position": 0,
            "state": self._state_payload(client),
        }

    def _waiting_payload(self, client: MiniRedisClient, user_id: str, rank: int) -> dict[str, object]:
        return {
            "status": "waiting",
            "user_id": user_id,
            "queue_position": rank + 1,
            "state": self._state_payload(client),
        }

    def _bootstrap_with(self, client: MiniRedisClient) -> None:
        client.set(self._stock_key(), str(len(self.config.seat_ids)), nx=True)
        client.set(self._active_count_key(), "0", nx=True)

    def _client(self) -> MiniRedisClient:
        return MiniRedisClient(self.redis_host, self.redis_port)

    @staticmethod
    def _read_int(raw: str | None) -> int:
        return int(raw) if raw is not None else 0

    def _base(self) -> str:
        return f"event:{self.config.event_id}"

    def _queue_key(self) -> str:
        return f"{self._base()}:queue"

    def _participants_key(self) -> str:
        return f"{self._base()}:participants"

    def _queue_token_key(self, user_id: str) -> str:
        return f"{self._base()}:queue-token:{user_id}"

    def _admission_key(self, user_id: str) -> str:
        return f"{self._base()}:admission:{user_id}"

    def _reservation_key(self, user_id: str) -> str:
        return f"{self._base()}:reservation:{user_id}"

    def _seat_holder_key(self, seat_id: str) -> str:
        return f"{self._base()}:seat:{seat_id}:holder"

    def _seat_lock_key(self, seat_id: str) -> str:
        return f"{self._base()}:seat:{seat_id}:lock"

    def _stock_key(self) -> str:
        return f"{self._base()}:stock"

    def _active_count_key(self) -> str:
        return f"{self._base()}:active-count"

    def _rate_key(self, user_id: str) -> str:
        return f"{self._base()}:rate:{user_id}"
