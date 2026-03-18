from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from mini_redis.client import MiniRedisClient
from ticketing_api.demo import render_demo_page
from ticketing_api.models import (
    CreateEventRequest,
    CreateEventResponse,
    ErrorResponse,
    EventSeatsResponse,
    EventStatusResponse,
    SeatActionResponse,
    UserActionRequest,
)
from ticketing_api.service import TicketingError, TicketingService
from ticketing_api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    redis_client = MiniRedisClient(settings.redis_host, settings.redis_port)
    service = TicketingService(redis_client=redis_client, hold_ttl_seconds=settings.hold_ttl_seconds)

    app = FastAPI(title="Mini Redis Ticketing API", version="0.1.0")
    app.state.settings = settings
    app.state.service = service

    @app.exception_handler(TicketingError)
    async def handle_ticketing_error(_: Request, exc: TicketingError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(reason=exc.reason).model_dump(),
        )

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/demo")

    @app.get("/demo", include_in_schema=False, response_class=HTMLResponse)
    async def demo_page() -> HTMLResponse:
        return HTMLResponse(render_demo_page(settings.hold_ttl_seconds))

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"success": True}

    @app.get("/health/full")
    async def full_health() -> JSONResponse:
        try:
            async with redis_client.connection() as connection:
                pong = await connection.execute("PING")
        except Exception as exc:  # pragma: no cover - exercised manually
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "api": True,
                    "redis": False,
                    "error": str(exc),
                    "holdTtlSeconds": settings.hold_ttl_seconds,
                },
            )

        return JSONResponse(
            content={
                "success": True,
                "api": True,
                "redis": pong == "PONG",
                "redisReply": pong,
                "holdTtlSeconds": settings.hold_ttl_seconds,
            }
        )

    @app.post("/events", response_model=CreateEventResponse, status_code=201)
    async def create_event(payload: CreateEventRequest) -> CreateEventResponse:
        return await service.create_event(payload)

    @app.get("/events/{event_id}/seats", response_model=EventSeatsResponse)
    async def list_seats(event_id: str) -> EventSeatsResponse:
        return await service.list_seats(event_id)

    @app.post("/events/{event_id}/seats/{seat_id}/hold", response_model=SeatActionResponse)
    async def hold_seat(event_id: str, seat_id: str, payload: UserActionRequest) -> SeatActionResponse:
        return await service.hold_seat(event_id, seat_id, payload.userId)

    @app.post("/events/{event_id}/seats/{seat_id}/confirm", response_model=SeatActionResponse)
    async def confirm_seat(event_id: str, seat_id: str, payload: UserActionRequest) -> SeatActionResponse:
        return await service.confirm_seat(event_id, seat_id, payload.userId)

    @app.post("/events/{event_id}/seats/{seat_id}/cancel", response_model=SeatActionResponse)
    async def cancel_seat(event_id: str, seat_id: str, payload: UserActionRequest) -> SeatActionResponse:
        return await service.cancel_seat(event_id, seat_id, payload.userId)

    @app.get("/events/{event_id}/status", response_model=EventStatusResponse)
    async def event_status(event_id: str) -> EventStatusResponse:
        return await service.event_status(event_id)

    return app
