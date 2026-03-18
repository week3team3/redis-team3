from __future__ import annotations

import asyncio

import httpx
import pytest

from mini_redis.server import MiniRedisServer
from ticketing_api.app import create_app
from ticketing_api.settings import Settings


@pytest.fixture
async def redis_server(unused_tcp_port: int):
    server = MiniRedisServer(host="127.0.0.1", port=unused_tcp_port, cleanup_interval=0.1)
    await server.start()
    try:
        yield server
    finally:
        await server.close()


@pytest.fixture
async def client(redis_server: MiniRedisServer):
    port = redis_server.sockets[0].getsockname()[1]
    app = create_app(
        Settings(
            redis_host="127.0.0.1",
            redis_port=port,
            hold_ttl_seconds=1,
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_event_lifecycle_hold_confirm_and_status(client: httpx.AsyncClient) -> None:
    create_response = await client.post(
        "/events",
        json={"eventId": "concert-001", "title": "Jungle Live", "seats": ["A1", "A2"]},
    )
    assert create_response.status_code == 201

    hold_response = await client.post(
        "/events/concert-001/seats/A1/hold",
        json={"userId": "user-01"},
    )
    assert hold_response.status_code == 200
    assert hold_response.json()["status"] == "HELD"

    confirm_response = await client.post(
        "/events/concert-001/seats/A1/confirm",
        json={"userId": "user-01"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "SOLD"

    seats_response = await client.get("/events/concert-001/seats")
    assert seats_response.status_code == 200
    seats = seats_response.json()["seats"]
    assert seats == [
        {"seatId": "A1", "status": "SOLD", "userId": "user-01", "ttl": None},
        {"seatId": "A2", "status": "AVAILABLE", "userId": None, "ttl": None},
    ]

    status_response = await client.get("/events/concert-001/status")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "eventId": "concert-001",
        "available": 1,
        "held": 0,
        "sold": 1,
    }


@pytest.mark.asyncio
async def test_demo_page_and_full_health_are_available(client: httpx.AsyncClient) -> None:
    demo_response = await client.get("/demo")
    assert demo_response.status_code == 200
    assert "Ticketing Control Room" in demo_response.text

    health_response = await client.get("/health/full")
    assert health_response.status_code == 200
    assert health_response.json() == {
        "success": True,
        "api": True,
        "redis": True,
        "redisReply": "PONG",
        "holdTtlSeconds": 1,
    }


@pytest.mark.asyncio
async def test_only_one_concurrent_hold_succeeds(client: httpx.AsyncClient) -> None:
    await client.post(
        "/events",
        json={"eventId": "concert-race", "title": "Race", "seats": ["A1"]},
    )

    async def attempt(index: int) -> httpx.Response:
        return await client.post(
            "/events/concert-race/seats/A1/hold",
            json={"userId": f"user-{index}"},
        )

    responses = await asyncio.gather(*(attempt(index) for index in range(100)))

    success_count = sum(response.status_code == 200 for response in responses)
    failure_count = sum(response.status_code == 409 for response in responses)

    assert success_count == 1
    assert failure_count == 99


@pytest.mark.asyncio
async def test_hold_expires_and_another_user_can_rehold(client: httpx.AsyncClient) -> None:
    await client.post(
        "/events",
        json={"eventId": "concert-expire", "title": "Expire", "seats": ["A1"]},
    )

    first_hold = await client.post(
        "/events/concert-expire/seats/A1/hold",
        json={"userId": "user-01"},
    )
    assert first_hold.status_code == 200

    await asyncio.sleep(1.2)

    second_hold = await client.post(
        "/events/concert-expire/seats/A1/hold",
        json={"userId": "user-02"},
    )
    assert second_hold.status_code == 200
    assert second_hold.json()["status"] == "HELD"
