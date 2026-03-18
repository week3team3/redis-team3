from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from uuid import uuid4

import httpx


async def create_event(client: httpx.AsyncClient, event_id: str, title: str, seats: list[str]) -> None:
    response = await client.post(
        "/events",
        json={"eventId": event_id, "title": title, "seats": seats},
    )
    response.raise_for_status()


async def run_same_seat(client: httpx.AsyncClient, concurrency: int) -> dict[str, object]:
    event_id = f"same-seat-{uuid4().hex[:8]}"
    await create_event(client, event_id, "Same Seat Battle", ["A1"])

    async def hold(index: int) -> httpx.Response:
        return await client.post(
            f"/events/{event_id}/seats/A1/hold",
            json={"userId": f"user-{index}"},
        )

    start = time.perf_counter()
    responses = await asyncio.gather(*(hold(index) for index in range(concurrency)))
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    success = sum(response.status_code == 200 for response in responses)
    failure = sum(response.status_code == 409 for response in responses)
    status_response = await client.get(f"/events/{event_id}/status")
    status_response.raise_for_status()

    return {
        "scenario": "same-seat",
        "eventId": event_id,
        "concurrency": concurrency,
        "elapsedMs": elapsed_ms,
        "success": success,
        "failure": failure,
        "status": status_response.json(),
    }


async def run_random_seats(client: httpx.AsyncClient, requests: int, seat_count: int) -> dict[str, object]:
    event_id = f"random-seats-{uuid4().hex[:8]}"
    seats = [f"A{index}" for index in range(1, seat_count + 1)]
    await create_event(client, event_id, "Random Seat Rush", seats)

    async def hold(index: int) -> tuple[str, str, httpx.Response]:
        seat_id = random.choice(seats)
        user_id = f"user-{index}"
        response = await client.post(
            f"/events/{event_id}/seats/{seat_id}/hold",
            json={"userId": user_id},
        )
        return seat_id, user_id, response

    start = time.perf_counter()
    attempts = await asyncio.gather(*(hold(index) for index in range(requests)))
    held_pairs = [(seat_id, user_id) for seat_id, user_id, response in attempts if response.status_code == 200]
    confirms = await asyncio.gather(
        *(
            client.post(
                f"/events/{event_id}/seats/{seat_id}/confirm",
                json={"userId": user_id},
            )
            for seat_id, user_id in held_pairs
        )
    )
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    confirmed = sum(response.status_code == 200 for response in confirms)
    status_response = await client.get(f"/events/{event_id}/status")
    status_response.raise_for_status()

    return {
        "scenario": "random-seats",
        "eventId": event_id,
        "requests": requests,
        "seatCount": seat_count,
        "elapsedMs": elapsed_ms,
        "holdSuccess": len(held_pairs),
        "confirmed": confirmed,
        "status": status_response.json(),
    }


async def run_expiry(client: httpx.AsyncClient) -> dict[str, object]:
    event_id = f"expiry-{uuid4().hex[:8]}"
    await create_event(client, event_id, "Expiry Flow", ["A1"])

    first_hold = await client.post(
        f"/events/{event_id}/seats/A1/hold",
        json={"userId": "user-first"},
    )
    first_hold.raise_for_status()

    seats_response = await client.get(f"/events/{event_id}/seats")
    seats_response.raise_for_status()
    ttl = seats_response.json()["seats"][0]["ttl"]
    await asyncio.sleep(ttl + 1)

    second_hold = await client.post(
        f"/events/{event_id}/seats/A1/hold",
        json={"userId": "user-second"},
    )
    status_response = await client.get(f"/events/{event_id}/status")
    status_response.raise_for_status()

    return {
        "scenario": "expiry",
        "eventId": event_id,
        "initialHoldStatus": first_hold.status_code,
        "reholdStatus": second_hold.status_code,
        "status": status_response.json(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run load test scenarios against the ticketing API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--scenario",
        choices=["all", "same-seat", "random-seats", "expiry"],
        default="all",
    )
    parser.add_argument("--concurrency", type=int, default=1000)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--seat-count", type=int, default=30)
    return parser


async def _run(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        results: list[dict[str, object]] = []
        if args.scenario in {"all", "same-seat"}:
            results.append(await run_same_seat(client, args.concurrency))
        if args.scenario in {"all", "random-seats"}:
            results.append(await run_random_seats(client, args.requests, args.seat_count))
        if args.scenario in {"all", "expiry"}:
            results.append(await run_expiry(client))

    print(json.dumps(results, indent=2))


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(_run(args))
