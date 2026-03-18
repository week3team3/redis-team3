"""
Mini Redis server with a ticketing simulation layer.

Why this server exists:
- RESP parsing shows how a TCP protocol server reads structured requests.
- The storage engine keeps key/value state, TTL, invalidation, and persistence in one place.
- Ticketing commands use the same storage engine to explain queue, hold, confirm, cancel,
  waiting-room promotion, and concurrent seat contention.

This is not a full Redis clone. It is a learning-oriented Mini Redis that focuses on:
- hash table style key/value storage
- RESP/TCP access
- concurrency safety
- TTL / invalidation
- ticketing-style verification on top of the storage engine
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


HOST = os.getenv("MINI_REDIS_HOST", "127.0.0.1")
PORT = int(os.getenv("MINI_REDIS_PORT", "6380"))
SWEEP_INTERVAL = float(os.getenv("MINI_REDIS_SWEEP_INTERVAL", "1.0"))
SNAPSHOT_PATH = os.getenv("MINI_REDIS_SNAPSHOT_PATH", "")


@dataclass
class Entry:
    data_type: str
    value: Any
    expires_at: float | None = None
    invalidated: bool = False
    invalidation_reason: str | None = None
    invalidated_at: float | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "data_type": self.data_type,
            "value": self.value,
            "expires_at": self.expires_at,
            "invalidated": self.invalidated,
            "invalidation_reason": self.invalidation_reason,
            "invalidated_at": self.invalidated_at,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "Entry":
        return cls(
            data_type=str(payload["data_type"]),
            value=payload["value"],
            expires_at=payload.get("expires_at"),
            invalidated=bool(payload.get("invalidated", False)),
            invalidation_reason=payload.get("invalidation_reason"),
            invalidated_at=payload.get("invalidated_at"),
        )


store: dict[str, Entry] = {}
store_lock = threading.RLock()
snapshot_file = Path(SNAPSHOT_PATH) if SNAPSHOT_PATH else None
stop_sweeper = threading.Event()


def load_snapshot() -> None:
    """Restore store content from a JSON snapshot if one is configured."""

    if snapshot_file is None or not snapshot_file.exists():
        return

    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[SNAPSHOT DISABLED] failed to read snapshot: {exc}")
        return

    now = time.time()
    with store_lock:
        store.clear()
        for key, record in payload.get("entries", {}).items():
            entry = Entry.from_record(record)
            if entry.expires_at is not None and entry.expires_at <= now:
                continue
            store[key] = entry


def save_snapshot_locked() -> None:
    """Write the current store into a JSON snapshot for restart recovery."""

    if snapshot_file is None:
        return

    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": time.time(),
        "entries": {key: entry.to_record() for key, entry in store.items()},
    }
    temp_path = snapshot_file.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(snapshot_file)


def purge_expired_key_locked(key: str) -> bool:
    """Remove a key if its TTL has already passed."""

    entry = store.get(key)
    if entry is None or entry.expires_at is None:
        return False
    if time.time() < entry.expires_at:
        return False
    store.pop(key, None)
    return True


def get_visible_entry_locked(key: str) -> Entry | None:
    """Return a visible entry, treating expired or invalidated entries as missing."""

    purge_expired_key_locked(key)
    entry = store.get(key)
    if entry is None:
        return None
    if entry.invalidated:
        return None
    return entry


def set_string_locked(key: str, value: str, *, ex: int | None = None) -> None:
    expires_at = None if ex is None else time.time() + ex
    store[key] = Entry(data_type="string", value=value, expires_at=expires_at)


def delete_key_locked(key: str) -> bool:
    existed = key in store
    store.pop(key, None)
    return existed


def read_string_locked(key: str) -> str | None:
    entry = get_visible_entry_locked(key)
    if entry is None:
        return None
    if entry.data_type != "string":
        raise ValueError("wrong type for operation")
    return str(entry.value)


def read_ttl_seconds_locked(key: str) -> int:
    purge_expired_key_locked(key)
    entry = store.get(key)
    if entry is None or entry.invalidated:
        return -2
    if entry.expires_at is None:
        return -1
    remaining = entry.expires_at - time.time()
    if remaining <= 0:
        store.pop(key, None)
        return -2
    return max(0, int(remaining))


def ensure_zset_locked(key: str) -> dict[str, float]:
    entry = get_visible_entry_locked(key)
    if entry is None:
        zset: dict[str, float] = {}
        store[key] = Entry(data_type="zset", value=zset)
        return zset
    if entry.data_type != "zset":
        raise ValueError("wrong type for operation")
    return entry.value


def get_zset_locked(key: str) -> dict[str, float] | None:
    entry = get_visible_entry_locked(key)
    if entry is None:
        return None
    if entry.data_type != "zset":
        raise ValueError("wrong type for operation")
    return entry.value


def zset_ordered_items_locked(key: str) -> list[tuple[str, float]]:
    zset = get_zset_locked(key)
    if zset is None:
        return []
    return sorted(zset.items(), key=lambda item: (item[1], item[0]))


def store_stats_locked() -> dict[str, int]:
    total = len(store)
    expiring = sum(1 for entry in store.values() if entry.expires_at is not None)
    invalidated = sum(1 for entry in store.values() if entry.invalidated)
    strings = sum(1 for entry in store.values() if entry.data_type == "string")
    zsets = sum(1 for entry in store.values() if entry.data_type == "zset")
    return {
        "total_keys": total,
        "expiring_keys": expiring,
        "invalidated_keys": invalidated,
        "string_keys": strings,
        "zset_keys": zsets,
    }


def event_prefix(event_id: str) -> str:
    return f"ticket:{event_id}:"


def event_meta_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}meta"


def event_active_limit_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}active_limit"


def event_hold_ttl_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}hold_ttl"


def event_active_count_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}active_count"


def event_queue_seq_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}queue_seq"


def event_queue_key(event_id: str) -> str:
    return f"{event_prefix(event_id)}waiting_queue"


def seat_key(event_id: str, seat_id: str) -> str:
    return f"{event_prefix(event_id)}seat:{seat_id}"


def reservation_key(event_id: str, user_id: str) -> str:
    return f"{event_prefix(event_id)}reservation:{user_id}"


def admitted_key(event_id: str, user_id: str) -> str:
    return f"{event_prefix(event_id)}admitted:{user_id}"


def clear_event_locked(event_id: str) -> None:
    prefix = event_prefix(event_id)
    for key in [key for key in list(store.keys()) if key.startswith(prefix)]:
        store.pop(key, None)


def load_event_meta_locked(event_id: str) -> dict[str, Any] | None:
    raw = read_string_locked(event_meta_key(event_id))
    if raw is None:
        return None
    return json.loads(raw)


def read_int_locked(key: str, default: int = 0) -> int:
    raw = read_string_locked(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError("value is not an integer") from exc


def write_int_locked(key: str, value: int) -> None:
    set_string_locked(key, str(value))


def increment_locked(key: str, amount: int = 1) -> int:
    next_value = read_int_locked(key, 0) + amount
    write_int_locked(key, next_value)
    return next_value


def get_admitted_users_locked(event_id: str) -> list[str]:
    prefix = f"{event_prefix(event_id)}admitted:"
    users = [key.removeprefix(prefix) for key in store if key.startswith(prefix) and get_visible_entry_locked(key) is not None]
    return sorted(users)


def release_admission_locked(event_id: str, user_id: str) -> None:
    if delete_key_locked(admitted_key(event_id, user_id)):
        current = read_int_locked(event_active_count_key(event_id), 0)
        write_int_locked(event_active_count_key(event_id), max(0, current - 1))


def promote_from_queue_locked(event_id: str) -> list[str]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return []

    promoted: list[str] = []
    limit = read_int_locked(event_active_limit_key(event_id), int(meta["active_limit"]))
    active_count = read_int_locked(event_active_count_key(event_id), 0)
    queue_key = event_queue_key(event_id)
    zset = get_zset_locked(queue_key)
    if zset is None:
        return promoted

    while active_count < limit:
        ordered = zset_ordered_items_locked(queue_key)
        if not ordered:
            break
        user_id, _ = ordered[0]
        zset.pop(user_id, None)

        if read_string_locked(admitted_key(event_id, user_id)) == "1":
            continue

        set_string_locked(admitted_key(event_id, user_id), "1")
        active_count += 1
        promoted.append(user_id)

    write_int_locked(event_active_count_key(event_id), active_count)
    return promoted


def cleanup_ticket_event_locked(event_id: str) -> None:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return

    changed = False
    released_users: list[str] = []

    for seat_id in meta["seats"]:
        raw = read_string_locked(seat_key(event_id, seat_id))
        if raw is None or not raw.startswith("HELD:"):
            continue
        user_id = raw.split(":", 1)[1]
        reservation_raw = read_string_locked(reservation_key(event_id, user_id))
        if reservation_raw == seat_id:
            continue
        set_string_locked(seat_key(event_id, seat_id), "AVAILABLE")
        released_users.append(user_id)
        changed = True

    for user_id in released_users:
        release_admission_locked(event_id, user_id)

    if changed:
        promote_from_queue_locked(event_id)


def cleanup_all_locked() -> None:
    for key in list(store.keys()):
        purge_expired_key_locked(key)

    for key in list(store.keys()):
        if key.endswith(":meta") and key.startswith("ticket:"):
            event_id = key.split(":")[1]
            cleanup_ticket_event_locked(event_id)


def ticket_state_locked(event_id: str) -> dict[str, Any]:
    cleanup_ticket_event_locked(event_id)
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    seats: list[dict[str, Any]] = []
    available = held = sold = 0

    for seat_id in meta["seats"]:
        raw = read_string_locked(seat_key(event_id, seat_id))
        ttl = None
        user_id = None

        if raw is None or raw == "AVAILABLE":
            status = "AVAILABLE"
            available += 1
        elif raw.startswith("HELD:"):
            status = "HELD"
            user_id = raw.split(":", 1)[1]
            ttl = read_ttl_seconds_locked(reservation_key(event_id, user_id))
            held += 1
        elif raw.startswith("SOLD:"):
            status = "SOLD"
            user_id = raw.split(":", 1)[1]
            sold += 1
        else:
            status = raw

        seats.append({"seat_id": seat_id, "status": status, "user_id": user_id, "ttl": ttl})

    queue = [
        {"user_id": member, "position": index + 1}
        for index, (member, _) in enumerate(zset_ordered_items_locked(event_queue_key(event_id)))
    ]

    reservations: list[dict[str, Any]] = []
    reservation_prefix = f"{event_prefix(event_id)}reservation:"
    for key in sorted(store.keys()):
        if not key.startswith(reservation_prefix):
            continue
        entry = get_visible_entry_locked(key)
        if entry is None or entry.data_type != "string":
            continue
        user_id = key.removeprefix(reservation_prefix)
        if isinstance(entry.value, str) and entry.value.startswith("{"):
            payload = json.loads(entry.value)
            reservations.append(payload)
            continue
        reservations.append(
            {
                "event_id": event_id,
                "user_id": user_id,
                "seat_id": str(entry.value),
                "status": "HELD",
                "ttl": read_ttl_seconds_locked(key),
            }
        )

    return {
        "ok": True,
        "event_id": event_id,
        "active_limit": read_int_locked(event_active_limit_key(event_id), int(meta["active_limit"])),
        "hold_seconds": read_int_locked(event_hold_ttl_key(event_id), int(meta["hold_seconds"])),
        "active_count": read_int_locked(event_active_count_key(event_id), 0),
        "queue_size": len(queue),
        "metrics": {
            "available": available,
            "held": held,
            "sold": sold,
            "total_seats": len(meta["seats"]),
        },
        "seats": seats,
        "admitted_users": get_admitted_users_locked(event_id),
        "waiting_users": queue,
        "reservations": reservations,
        "store_stats": store_stats_locked(),
    }


def ticket_status_locked(event_id: str, user_id: str) -> dict[str, Any]:
    cleanup_ticket_event_locked(event_id)
    state = ticket_state_locked(event_id)
    if not state["ok"]:
        return state

    reservation_raw = read_string_locked(reservation_key(event_id, user_id))
    if reservation_raw is not None:
        if reservation_raw.startswith("{"):
            payload = json.loads(reservation_raw)
            payload["ok"] = True
            return payload
        return {
            "ok": True,
            "status": "HELD",
            "event_id": event_id,
            "user_id": user_id,
            "seat_id": reservation_raw,
            "ttl": read_ttl_seconds_locked(reservation_key(event_id, user_id)),
        }

    if read_string_locked(admitted_key(event_id, user_id)) == "1":
        return {"ok": True, "status": "ADMITTED", "event_id": event_id, "user_id": user_id}

    for item in state["waiting_users"]:
        if item["user_id"] == user_id:
            return {
                "ok": True,
                "status": "WAITING",
                "event_id": event_id,
                "user_id": user_id,
                "position": item["position"],
            }

    return {"ok": True, "status": "NONE", "event_id": event_id, "user_id": user_id}


def ticket_init_locked(event_id: str, active_limit: int, hold_seconds: int, seats: list[str]) -> dict[str, Any]:
    clear_event_locked(event_id)
    meta = {"event_id": event_id, "active_limit": active_limit, "hold_seconds": hold_seconds, "seats": seats}
    set_string_locked(event_meta_key(event_id), json.dumps(meta, ensure_ascii=True))
    write_int_locked(event_active_limit_key(event_id), active_limit)
    write_int_locked(event_hold_ttl_key(event_id), hold_seconds)
    write_int_locked(event_active_count_key(event_id), 0)
    write_int_locked(event_queue_seq_key(event_id), 0)
    ensure_zset_locked(event_queue_key(event_id))
    for seat_id in seats:
        set_string_locked(seat_key(event_id, seat_id), "AVAILABLE")
    return ticket_state_locked(event_id)


def ticket_enter_locked(event_id: str, user_id: str) -> dict[str, Any]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    cleanup_ticket_event_locked(event_id)
    existing = ticket_status_locked(event_id, user_id)
    if existing["status"] in {"ADMITTED", "WAITING", "HELD", "CONFIRMED"}:
        return existing

    active_limit = read_int_locked(event_active_limit_key(event_id), int(meta["active_limit"]))
    active_count = read_int_locked(event_active_count_key(event_id), 0)
    queue_key = event_queue_key(event_id)
    queue_size = len(zset_ordered_items_locked(queue_key))

    if active_count < active_limit and queue_size == 0:
        set_string_locked(admitted_key(event_id, user_id), "1")
        write_int_locked(event_active_count_key(event_id), active_count + 1)
        return {"ok": True, "status": "ADMITTED", "event_id": event_id, "user_id": user_id}

    next_seq = increment_locked(event_queue_seq_key(event_id), 1)
    zset = ensure_zset_locked(queue_key)
    zset[user_id] = float(next_seq)
    position = len(zset_ordered_items_locked(queue_key))
    return {"ok": True, "status": "WAITING", "event_id": event_id, "user_id": user_id, "position": position}


def ticket_exit_locked(event_id: str, user_id: str) -> dict[str, Any]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    cleanup_ticket_event_locked(event_id)
    reservation = read_string_locked(reservation_key(event_id, user_id))
    if reservation is not None:
        return {"ok": False, "reason": "reservation_exists", "event_id": event_id, "user_id": user_id}

    if read_string_locked(admitted_key(event_id, user_id)) == "1":
        release_admission_locked(event_id, user_id)
        promoted = promote_from_queue_locked(event_id)
        return {"ok": True, "status": "EXITED", "user_id": user_id, "promoted": promoted}

    queue = get_zset_locked(event_queue_key(event_id))
    if queue is not None and user_id in queue:
        queue.pop(user_id, None)
        return {"ok": True, "status": "REMOVED_FROM_QUEUE", "user_id": user_id}

    return {"ok": True, "status": "NONE", "user_id": user_id}


def ticket_hold_locked(event_id: str, user_id: str, seat_id: str) -> dict[str, Any]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    if seat_id not in meta["seats"]:
        return {"ok": False, "reason": "unknown_seat", "seat_id": seat_id}

    cleanup_ticket_event_locked(event_id)
    if read_string_locked(admitted_key(event_id, user_id)) != "1":
        return {"ok": False, "reason": "not_admitted", "user_id": user_id}

    if read_string_locked(reservation_key(event_id, user_id)) is not None:
        return {"ok": False, "reason": "already_holding", "user_id": user_id}

    current = read_string_locked(seat_key(event_id, seat_id))
    if current not in {None, "AVAILABLE"}:
        owner = current.split(":", 1)[1] if ":" in current else None
        return {"ok": False, "reason": "seat_not_available", "seat_id": seat_id, "owner": owner}

    hold_seconds = read_int_locked(event_hold_ttl_key(event_id), int(meta["hold_seconds"]))
    set_string_locked(seat_key(event_id, seat_id), f"HELD:{user_id}")
    set_string_locked(reservation_key(event_id, user_id), seat_id, ex=hold_seconds)
    return {
        "ok": True,
        "status": "HELD",
        "event_id": event_id,
        "user_id": user_id,
        "seat_id": seat_id,
        "ttl": hold_seconds,
    }


def ticket_confirm_locked(event_id: str, user_id: str) -> dict[str, Any]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    cleanup_ticket_event_locked(event_id)
    seat_id = read_string_locked(reservation_key(event_id, user_id))
    if seat_id is None or seat_id.startswith("{"):
        return {"ok": False, "reason": "hold_not_found", "user_id": user_id}

    current = read_string_locked(seat_key(event_id, seat_id))
    if current != f"HELD:{user_id}":
        return {"ok": False, "reason": "seat_not_held_by_user", "seat_id": seat_id}

    set_string_locked(seat_key(event_id, seat_id), f"SOLD:{user_id}")
    confirmed_payload = {
        "status": "CONFIRMED",
        "event_id": event_id,
        "user_id": user_id,
        "seat_id": seat_id,
        "confirmed_at": time.time(),
    }
    set_string_locked(reservation_key(event_id, user_id), json.dumps(confirmed_payload, ensure_ascii=True))
    release_admission_locked(event_id, user_id)
    promoted = promote_from_queue_locked(event_id)
    confirmed_payload["ok"] = True
    confirmed_payload["promoted"] = promoted
    return confirmed_payload


def ticket_cancel_locked(event_id: str, user_id: str) -> dict[str, Any]:
    meta = load_event_meta_locked(event_id)
    if meta is None:
        return {"ok": False, "reason": "event_not_found", "event_id": event_id}

    cleanup_ticket_event_locked(event_id)
    seat_id = read_string_locked(reservation_key(event_id, user_id))
    if seat_id is None or seat_id.startswith("{"):
        return {"ok": False, "reason": "hold_not_found", "user_id": user_id}

    current = read_string_locked(seat_key(event_id, seat_id))
    if current == f"HELD:{user_id}":
        set_string_locked(seat_key(event_id, seat_id), "AVAILABLE")

    delete_key_locked(reservation_key(event_id, user_id))
    release_admission_locked(event_id, user_id)
    promoted = promote_from_queue_locked(event_id)
    return {
        "ok": True,
        "status": "CANCELLED",
        "event_id": event_id,
        "user_id": user_id,
        "seat_id": seat_id,
        "promoted": promoted,
    }


def sweep_loop() -> None:
    while not stop_sweeper.wait(SWEEP_INTERVAL):
        with store_lock:
            cleanup_all_locked()
            save_snapshot_locked()


def parse_resp(buffer: bytes) -> tuple[Optional[list[str]], int]:
    """Parse one RESP array command from the current buffer."""

    if not buffer:
        return None, 0
    if buffer[:1] != b"*":
        raise ValueError("expected RESP array request")

    first_line_end = buffer.find(b"\r\n")
    if first_line_end == -1:
        return None, 0

    try:
        arg_count = int(buffer[1:first_line_end].decode())
    except ValueError as exc:
        raise ValueError("invalid array length") from exc

    index = first_line_end + 2
    tokens: list[str] = []

    for _ in range(arg_count):
        if index >= len(buffer):
            return None, 0
        if buffer[index:index + 1] != b"$":
            raise ValueError("expected bulk string")

        bulk_len_end = buffer.find(b"\r\n", index)
        if bulk_len_end == -1:
            return None, 0

        try:
            bulk_len = int(buffer[index + 1:bulk_len_end].decode())
        except ValueError as exc:
            raise ValueError("invalid bulk string length") from exc

        if bulk_len < 0:
            raise ValueError("negative bulk string length is not allowed in requests")

        value_start = bulk_len_end + 2
        value_end = value_start + bulk_len
        if value_end + 2 > len(buffer):
            return None, 0
        if buffer[value_end:value_end + 2] != b"\r\n":
            raise ValueError("bulk string missing CRLF terminator")

        tokens.append(buffer[value_start:value_end].decode())
        index = value_end + 2

    return tokens, index


def handle_command(tokens: list[str]) -> tuple[str, str | int | None]:
    """Execute one command against the shared in-memory store."""

    if not tokens:
        return "error", "empty command"

    command = tokens[0].upper()

    with store_lock:
        cleanup_all_locked()

        if command == "PING":
            return "simple", tokens[1] if len(tokens) == 2 else "PONG"

        if command == "SET":
            if len(tokens) < 3:
                return "error", "wrong number of arguments for SET"

            key, value = tokens[1], tokens[2]
            nx = False
            ex: int | None = None
            index = 3
            while index < len(tokens):
                option = tokens[index].upper()
                if option == "NX":
                    nx = True
                    index += 1
                    continue
                if option == "EX" and index + 1 < len(tokens):
                    try:
                        ex = int(tokens[index + 1])
                    except ValueError:
                        return "error", "invalid expire time"
                    index += 2
                    continue
                return "error", "syntax error"

            if nx and get_visible_entry_locked(key) is not None:
                return "bulk", None
            set_string_locked(key, value, ex=ex)
            save_snapshot_locked()
            return "simple", "OK"

        if command == "SETNX":
            if len(tokens) != 3:
                return "error", "wrong number of arguments for SETNX"
            if get_visible_entry_locked(tokens[1]) is not None:
                return "integer", 0
            set_string_locked(tokens[1], tokens[2])
            save_snapshot_locked()
            return "integer", 1

        if command == "GET":
            if len(tokens) != 2:
                return "error", "wrong number of arguments for GET"
            return "bulk", read_string_locked(tokens[1])

        if command == "DEL":
            if len(tokens) < 2:
                return "error", "wrong number of arguments for DEL"
            deleted = 0
            for key in tokens[1:]:
                deleted += 1 if delete_key_locked(key) else 0
            save_snapshot_locked()
            return "integer", deleted

        if command == "EXISTS":
            if len(tokens) < 2:
                return "error", "wrong number of arguments for EXISTS"
            count = sum(1 for key in tokens[1:] if get_visible_entry_locked(key) is not None)
            return "integer", count

        if command == "EXPIRE":
            if len(tokens) != 3:
                return "error", "wrong number of arguments for EXPIRE"
            entry = get_visible_entry_locked(tokens[1])
            if entry is None:
                return "integer", 0
            try:
                seconds = int(tokens[2])
            except ValueError:
                return "error", "TTL must be an integer"
            if seconds < 0:
                return "error", "TTL must be zero or positive"
            entry.expires_at = time.time() + seconds
            save_snapshot_locked()
            return "integer", 1

        if command == "TTL":
            if len(tokens) != 2:
                return "error", "wrong number of arguments for TTL"
            return "integer", read_ttl_seconds_locked(tokens[1])

        if command == "INVALIDATE":
            if len(tokens) < 2:
                return "error", "wrong number of arguments for INVALIDATE"
            key = tokens[1]
            entry = get_visible_entry_locked(key)
            if entry is None:
                return "integer", 0
            entry.invalidated = True
            entry.invalidation_reason = " ".join(tokens[2:]) if len(tokens) > 2 else None
            entry.invalidated_at = time.time()
            save_snapshot_locked()
            return "integer", 1

        if command in {"INCR", "DECR"}:
            if len(tokens) != 2:
                return "error", f"wrong number of arguments for {command}"
            current = read_int_locked(tokens[1], 0)
            current = current + 1 if command == "INCR" else current - 1
            set_string_locked(tokens[1], str(current))
            save_snapshot_locked()
            return "integer", current

        if command == "SETIFEQ":
            if len(tokens) != 4:
                return "error", "wrong number of arguments for SETIFEQ"
            current = read_string_locked(tokens[1])
            if current != tokens[2]:
                return "integer", 0
            set_string_locked(tokens[1], tokens[3])
            save_snapshot_locked()
            return "integer", 1

        if command == "DELIFEQ":
            if len(tokens) != 3:
                return "error", "wrong number of arguments for DELIFEQ"
            current = read_string_locked(tokens[1])
            if current != tokens[2]:
                return "integer", 0
            delete_key_locked(tokens[1])
            save_snapshot_locked()
            return "integer", 1

        if command == "ZADD":
            if len(tokens) != 4:
                return "error", "wrong number of arguments for ZADD"
            try:
                score = float(tokens[2])
            except ValueError:
                return "error", "score is not a float"
            zset = ensure_zset_locked(tokens[1])
            created = 0 if tokens[3] in zset else 1
            zset[tokens[3]] = score
            save_snapshot_locked()
            return "integer", created

        if command == "ZRANK":
            if len(tokens) != 3:
                return "error", "wrong number of arguments for ZRANK"
            ordered = zset_ordered_items_locked(tokens[1])
            for index, (member, _) in enumerate(ordered):
                if member == tokens[2]:
                    return "integer", index
            return "bulk", None

        if command == "ZRANGE":
            if len(tokens) != 4:
                return "error", "wrong number of arguments for ZRANGE"
            try:
                start = int(tokens[2])
                stop = int(tokens[3])
            except ValueError:
                return "error", "start/stop must be integers"
            members = [member for member, _ in zset_ordered_items_locked(tokens[1])]
            if stop == -1:
                slice_members = members[start:]
            else:
                slice_members = members[start:stop + 1]
            return "bulk", json.dumps(slice_members, ensure_ascii=True)

        if command == "ZPOPMIN":
            if len(tokens) != 2:
                return "error", "wrong number of arguments for ZPOPMIN"
            zset = get_zset_locked(tokens[1])
            if not zset:
                return "bulk", None
            member, score = zset_ordered_items_locked(tokens[1])[0]
            zset.pop(member, None)
            save_snapshot_locked()
            return "bulk", json.dumps({"member": member, "score": score}, ensure_ascii=True)

        if command == "ZCARD":
            if len(tokens) != 2:
                return "error", "wrong number of arguments for ZCARD"
            zset = get_zset_locked(tokens[1])
            return "integer", 0 if zset is None else len(zset)

        if command == "ZREM":
            if len(tokens) != 3:
                return "error", "wrong number of arguments for ZREM"
            zset = get_zset_locked(tokens[1])
            if zset is None:
                return "integer", 0
            removed = 1 if tokens[2] in zset else 0
            zset.pop(tokens[2], None)
            save_snapshot_locked()
            return "integer", removed

        if command == "INFO":
            return "bulk", json.dumps(store_stats_locked(), ensure_ascii=True)

        if command == "TICKET_INIT":
            if len(tokens) < 5:
                return "error", "usage: TICKET_INIT <event> <active_limit> <hold_seconds> <seat...>"
            try:
                active_limit = int(tokens[2])
                hold_seconds = int(tokens[3])
            except ValueError:
                return "error", "active_limit and hold_seconds must be integers"
            if active_limit <= 0 or hold_seconds <= 0:
                return "error", "active_limit and hold_seconds must be positive"
            seats = tokens[4:]
            if len(set(seats)) != len(seats):
                return "error", "seat ids must be unique"
            payload = ticket_init_locked(tokens[1], active_limit, hold_seconds, seats)
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_RESET":
            if len(tokens) != 2:
                return "error", "usage: TICKET_RESET <event>"
            meta = load_event_meta_locked(tokens[1])
            if meta is None:
                return "error", "event not found"
            payload = ticket_init_locked(tokens[1], int(meta["active_limit"]), int(meta["hold_seconds"]), list(meta["seats"]))
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_ENTER":
            if len(tokens) != 3:
                return "error", "usage: TICKET_ENTER <event> <user>"
            payload = ticket_enter_locked(tokens[1], tokens[2])
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_STATUS":
            if len(tokens) != 3:
                return "error", "usage: TICKET_STATUS <event> <user>"
            payload = ticket_status_locked(tokens[1], tokens[2])
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_EXIT":
            if len(tokens) != 3:
                return "error", "usage: TICKET_EXIT <event> <user>"
            payload = ticket_exit_locked(tokens[1], tokens[2])
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_HOLD":
            if len(tokens) != 4:
                return "error", "usage: TICKET_HOLD <event> <user> <seat>"
            payload = ticket_hold_locked(tokens[1], tokens[2], tokens[3])
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_CONFIRM":
            if len(tokens) != 3:
                return "error", "usage: TICKET_CONFIRM <event> <user>"
            payload = ticket_confirm_locked(tokens[1], tokens[2])
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_CANCEL":
            if len(tokens) != 3:
                return "error", "usage: TICKET_CANCEL <event> <user>"
            payload = ticket_cancel_locked(tokens[1], tokens[2])
            save_snapshot_locked()
            return "bulk", json.dumps(payload, ensure_ascii=True)

        if command == "TICKET_STATE":
            if len(tokens) != 2:
                return "error", "usage: TICKET_STATE <event>"
            payload = ticket_state_locked(tokens[1])
            return "bulk", json.dumps(payload, ensure_ascii=True)

        return "error", f"unknown command '{tokens[0]}'"


def build_resp_response(kind: str, value: str | int | None) -> bytes:
    """Convert an internal response tuple into RESP bytes."""

    if kind == "simple":
        return f"+{value}\r\n".encode()

    if kind == "bulk":
        if value is None:
            return b"$-1\r\n"
        text = str(value)
        return f"${len(text)}\r\n{text}\r\n".encode()

    if kind == "integer":
        return f":{value}\r\n".encode()

    if kind == "error":
        return f"-ERR {value}\r\n".encode()

    return b"-ERR internal server error\r\n"


def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
    print(f"[CONNECT] {addr}")
    buffer = b""

    with conn:
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    print(f"[DISCONNECT] {addr}")
                    break

                buffer += chunk
                while buffer:
                    try:
                        tokens, consumed = parse_resp(buffer)
                    except ValueError as exc:
                        conn.sendall(build_resp_response("error", str(exc)))
                        buffer = b""
                        break

                    if tokens is None:
                        break

                    kind, value = handle_command(tokens)
                    conn.sendall(build_resp_response(kind, value))
                    buffer = buffer[consumed:]
            except ConnectionResetError:
                print(f"[RESET] {addr}")
                break


def run_server() -> None:
    load_snapshot()
    sweeper = threading.Thread(target=sweep_loop, daemon=True)
    sweeper.start()

    print(f"Mini RESP Redis server listening on {HOST}:{PORT}")
    if snapshot_file is None:
        print("Persistence disabled. Restart will reset the in-memory store.")
    else:
        print(f"Snapshot persistence enabled at {snapshot_file}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        try:
            while True:
                conn, addr = server_socket.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
        finally:
            stop_sweeper.set()
            with store_lock:
                save_snapshot_locked()


if __name__ == "__main__":
    run_server()
