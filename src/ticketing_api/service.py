from __future__ import annotations

import json
from dataclasses import dataclass

from mini_redis.client import MiniRedisClient, MiniRedisConnection
from ticketing_api.models import (
    CreateEventRequest,
    CreateEventResponse,
    EventSeatsResponse,
    EventStatusResponse,
    SeatActionResponse,
    SeatStatus,
    SeatView,
)


@dataclass(slots=True)
class EventMeta:
    event_id: str
    title: str
    seats: list[str]


class TicketingError(Exception):
    def __init__(self, status_code: int, reason: str) -> None:
        self.status_code = status_code
        self.reason = reason
        super().__init__(reason)


class TicketingService:
    def __init__(self, redis_client: MiniRedisClient, hold_ttl_seconds: int = 30) -> None:
        self.redis_client = redis_client
        self.hold_ttl_seconds = hold_ttl_seconds

    async def create_event(self, request: CreateEventRequest) -> CreateEventResponse:
        if len(set(request.seats)) != len(request.seats):
            raise TicketingError(409, "DUPLICATE_SEAT_IDS")

        meta = {
            "eventId": request.eventId,
            "title": request.title,
            "seats": request.seats,
        }
        async with self.redis_client.connection() as connection:
            result = await connection.execute("SET", self._event_key(request.eventId), json.dumps(meta), "NX")

        if result != "OK":
            raise TicketingError(409, "EVENT_ALREADY_EXISTS")
        return CreateEventResponse(eventId=request.eventId)

    async def list_seats(self, event_id: str) -> EventSeatsResponse:
        async with self.redis_client.connection() as connection:
            event = await self._load_event(connection, event_id)
            seats = [await self._read_seat_view(connection, event_id, seat_id) for seat_id in event.seats]
        return EventSeatsResponse(eventId=event_id, seats=seats)

    async def hold_seat(self, event_id: str, seat_id: str, user_id: str) -> SeatActionResponse:
        async with self.redis_client.connection() as connection:
            await self._ensure_seat_exists(connection, event_id, seat_id)
            result = await connection.execute(
                "SET",
                self._seat_key(event_id, seat_id),
                self._held_value(user_id),
                "NX",
                "EX",
                str(self.hold_ttl_seconds),
            )

        if result != "OK":
            raise TicketingError(409, "SEAT_NOT_AVAILABLE")
        return SeatActionResponse(seatId=seat_id, status=SeatStatus.HELD, ttl=self.hold_ttl_seconds)

    async def confirm_seat(self, event_id: str, seat_id: str, user_id: str) -> SeatActionResponse:
        async with self.redis_client.connection() as connection:
            await self._ensure_seat_exists(connection, event_id, seat_id)
            updated = await connection.execute(
                "SETIFEQ",
                self._seat_key(event_id, seat_id),
                self._held_value(user_id),
                self._sold_value(user_id),
            )

        if updated != 1:
            raise TicketingError(409, "SEAT_NOT_HELD_BY_USER")
        return SeatActionResponse(seatId=seat_id, status=SeatStatus.SOLD)

    async def cancel_seat(self, event_id: str, seat_id: str, user_id: str) -> SeatActionResponse:
        async with self.redis_client.connection() as connection:
            await self._ensure_seat_exists(connection, event_id, seat_id)
            deleted = await connection.execute(
                "DELIFEQ",
                self._seat_key(event_id, seat_id),
                self._held_value(user_id),
            )

        if deleted != 1:
            raise TicketingError(409, "SEAT_NOT_HELD_BY_USER")
        return SeatActionResponse(seatId=seat_id, status=SeatStatus.AVAILABLE)

    async def event_status(self, event_id: str) -> EventStatusResponse:
        async with self.redis_client.connection() as connection:
            event = await self._load_event(connection, event_id)
            seats = [await self._read_seat_view(connection, event_id, seat_id) for seat_id in event.seats]

        available = sum(seat.status == SeatStatus.AVAILABLE for seat in seats)
        held = sum(seat.status == SeatStatus.HELD for seat in seats)
        sold = sum(seat.status == SeatStatus.SOLD for seat in seats)
        return EventStatusResponse(eventId=event_id, available=available, held=held, sold=sold)

    async def _ensure_seat_exists(self, connection: MiniRedisConnection, event_id: str, seat_id: str) -> EventMeta:
        event = await self._load_event(connection, event_id)
        if seat_id not in event.seats:
            raise TicketingError(404, "SEAT_NOT_FOUND")
        return event

    async def _load_event(self, connection: MiniRedisConnection, event_id: str) -> EventMeta:
        raw = await connection.execute("GET", self._event_key(event_id))
        if raw is None:
            raise TicketingError(404, "EVENT_NOT_FOUND")
        payload = json.loads(str(raw))
        return EventMeta(
            event_id=payload["eventId"],
            title=payload["title"],
            seats=list(payload["seats"]),
        )

    async def _read_seat_view(self, connection: MiniRedisConnection, event_id: str, seat_id: str) -> SeatView:
        raw = await connection.execute("GET", self._seat_key(event_id, seat_id))
        if raw is None:
            return SeatView(seatId=seat_id, status=SeatStatus.AVAILABLE)

        value = str(raw)
        status, user_id = value.split(":", 1)
        if status == SeatStatus.HELD.value:
            ttl = await connection.execute("TTL", self._seat_key(event_id, seat_id))
            if not isinstance(ttl, int) or ttl <= 0:
                return SeatView(seatId=seat_id, status=SeatStatus.AVAILABLE)
            return SeatView(seatId=seat_id, status=SeatStatus.HELD, userId=user_id, ttl=ttl)
        if status == SeatStatus.SOLD.value:
            return SeatView(seatId=seat_id, status=SeatStatus.SOLD, userId=user_id)
        raise TicketingError(500, "INVALID_SEAT_STATE")

    @staticmethod
    def _event_key(event_id: str) -> str:
        return f"event:{event_id}:meta"

    @staticmethod
    def _seat_key(event_id: str, seat_id: str) -> str:
        return f"seat:{event_id}:{seat_id}"

    @staticmethod
    def _held_value(user_id: str) -> str:
        return f"{SeatStatus.HELD.value}:{user_id}"

    @staticmethod
    def _sold_value(user_id: str) -> str:
        return f"{SeatStatus.SOLD.value}:{user_id}"
