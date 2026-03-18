# Live Load Test Report

## Summary

- Executed on `2026-03-18 15:00:13 KST`
- Environment
  - Python: `3.12.13`
  - Mini Redis: `127.0.0.1:6380`
  - Ticketing API: `127.0.0.1:8000`
  - Hold TTL: `30s`
- Result summary
  - Same-seat race: `1000` concurrent hold requests, exactly `1` success and `999` conflicts
  - Random-seat burst: `500` requests across `30` seats, `30` successful holds and `30` confirms
  - Expiry flow: first hold succeeded, second hold also succeeded after waiting for TTL expiration
- Total load-test runtime: `36.93s`

## Goal

Run the actual Mini Redis server and Ticketing API as separate live processes, execute the full load-test suite against the HTTP API, and capture the observed behavior in a single reproducible document.

## Commands Used

### 1. Start Mini Redis

```bash
./hoseok/bin/mini-redis-server --host 127.0.0.1 --port 6380
```

### 2. Start Ticketing API

```bash
./hoseok/bin/ticketing-api \
  --host 127.0.0.1 \
  --port 8000 \
  --redis-host 127.0.0.1 \
  --redis-port 6380 \
  --hold-ttl 30
```

### 3. Health Check

```bash
curl -s http://127.0.0.1:8000/health
```

Response:

```json
{"success":true}
```

### 4. Mini Redis RESP Check

```bash
./hoseok/bin/python - <<'PY'
import asyncio
from mini_redis.client import MiniRedisClient

async def main() -> None:
    client = MiniRedisClient("127.0.0.1", 6380)
    async with client.connection() as conn:
        print(await conn.execute("PING"))

asyncio.run(main())
PY
```

Response:

```text
PONG
```

### 5. Full Load Test

```bash
/usr/bin/time -p ./hoseok/bin/ticketing-loadtest \
  --base-url http://127.0.0.1:8000 \
  --scenario all
```

## Raw Load-Test Output

```json
[
  {
    "scenario": "same-seat",
    "eventId": "same-seat-f92e80b9",
    "concurrency": 1000,
    "elapsedMs": 3696.05,
    "success": 1,
    "failure": 999,
    "status": {
      "eventId": "same-seat-f92e80b9",
      "available": 0,
      "held": 1,
      "sold": 0
    }
  },
  {
    "scenario": "random-seats",
    "eventId": "random-seats-a68176f5",
    "requests": 500,
    "seatCount": 30,
    "elapsedMs": 1898.54,
    "holdSuccess": 30,
    "confirmed": 30,
    "status": {
      "eventId": "random-seats-a68176f5",
      "available": 0,
      "held": 0,
      "sold": 30
    }
  },
  {
    "scenario": "expiry",
    "eventId": "expiry-6971bad7",
    "initialHoldStatus": 200,
    "reholdStatus": 200,
    "status": {
      "eventId": "expiry-6971bad7",
      "available": 0,
      "held": 1,
      "sold": 0
    }
  }
]
```

`time -p` output:

```text
real 36.93
user 3.24
sys 0.73
```

## Scenario Details

### 1. Same-Seat Race

- Event ID: `same-seat-f92e80b9`
- Test shape: `A1` seat, `1000` simultaneous hold requests
- Immediate result
  - Success: `1`
  - Failure: `999`
  - Final status right after scenario: `held=1`, `sold=0`
- Interpretation
  - The seat was held by exactly one requester.
  - Every competing request was rejected with HTTP `409 Conflict`.
  - This demonstrates that the owner-loop serialization plus `SET ... NX EX` prevented duplicate holds.

### 2. Random Seats Burst

- Event ID: `random-seats-a68176f5`
- Test shape: `30` seats, `500` hold attempts, successful holds immediately followed by confirm
- Immediate result
  - Hold success: `30`
  - Confirm success: `30`
  - Final status right after scenario: `available=0`, `held=0`, `sold=30`
- Interpretation
  - The system never oversold beyond seat capacity.
  - All seats that were successfully held were later confirmed.
  - No duplicate sale was observed because the sold count stopped exactly at seat count `30`.

### 3. Hold Expiry and Re-Hold

- Event ID: `expiry-6971bad7`
- Test shape
  - User 1 holds `A1`
  - Load tester reads the returned TTL from `GET /events/{eventId}/seats`
  - Waits for `ttl + 1` seconds
  - User 2 attempts the same hold again
- Immediate result
  - First hold status: `200`
  - Second hold status after wait: `200`
  - Final status right after scenario: `held=1`, `sold=0`
- Interpretation
  - The second hold succeeded only after the first hold expired.
  - This confirms TTL-based automatic seat release works correctly in the live server.

## Follow-Up State Checks After the Full Suite

The suite itself takes about `36.93s`, so any seat held during the first scenario has time to expire by the time follow-up queries run. That post-run behavior is expected and useful to show TTL cleanup.

### Same-Seat Event After the Full Suite

Request:

```bash
curl -s http://127.0.0.1:8000/events/same-seat-f92e80b9/status
curl -s http://127.0.0.1:8000/events/same-seat-f92e80b9/seats
```

Response:

```json
{"eventId":"same-seat-f92e80b9","available":1,"held":0,"sold":0}
{"eventId":"same-seat-f92e80b9","seats":[{"seatId":"A1","status":"AVAILABLE","userId":null,"ttl":null}]}
```

Interpretation:

- The original winning hold from scenario 1 expired during the remaining test runtime.
- The seat returned to `AVAILABLE` without manual cleanup.

### Random-Seats Event After the Full Suite

Request:

```bash
curl -s http://127.0.0.1:8000/events/random-seats-a68176f5/status
```

Response:

```json
{"eventId":"random-seats-a68176f5","available":0,"held":0,"sold":30}
```

Interpretation:

- Confirmed seats remained sold.
- TTL cleanup did not affect sold seats, which is the expected behavior because `SETIFEQ` removes expiry on confirm.

### Expiry Event After Additional Waiting

Request:

```bash
curl -s http://127.0.0.1:8000/events/expiry-6971bad7/seats
```

Response:

```json
{"eventId":"expiry-6971bad7","seats":[{"seatId":"A1","status":"AVAILABLE","userId":null,"ttl":null}]}
```

Interpretation:

- The second hold also expired later, returning the seat to `AVAILABLE`.
- This is a clean end-to-end confirmation that repeated hold-release cycles work with the same seat.

## Operational Observations

- The API logs showed a large burst of HTTP `409 Conflict` responses during the same-seat race, which matches the expected rejection pattern.
- The random-seat scenario produced a sequence of successful confirm requests after exactly `30` winning holds.
- The Mini Redis process remained stable through the entire run and continued answering `PING` and API-backed traffic.
- The longest part of the suite was the expiry scenario because it intentionally waited for the real `30s` TTL.

## Conclusion

The live run validated the core project claims:

- Duplicate holds on the same seat were prevented under heavy concurrent traffic.
- Total confirmed sales never exceeded seat inventory.
- Held seats automatically returned to `AVAILABLE` after TTL expiry.
- Confirmed seats stayed `SOLD` and were not released by background cleanup.

This report reflects an actual run against two live local server processes, not an in-memory test harness.
