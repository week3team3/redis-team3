from __future__ import annotations

import argparse
import socketserver
import threading
from typing import Iterable

from mini_redis.protocol import RESPError, encode_text_response, parse_resp
from mini_redis.store import MiniRedisStore


class MiniRedisTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[socketserver.BaseRequestHandler],
        store: MiniRedisStore | None = None,
        sweep_interval: float = 1.0,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.store = store or MiniRedisStore()
        self._sweep_interval = sweep_interval
        self._stop_event = threading.Event()
        self._sweeper_thread = threading.Thread(target=self._sweeper_loop, daemon=True)

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        if not self._sweeper_thread.is_alive():
            self._sweeper_thread.start()
        super().serve_forever(poll_interval=poll_interval)

    def shutdown(self) -> None:
        self._stop_event.set()
        super().shutdown()
        if self._sweeper_thread.is_alive():
            self._sweeper_thread.join(timeout=1)

    def _sweeper_loop(self) -> None:
        while not self._stop_event.wait(self._sweep_interval):
            self.store.cleanup()


class MiniRedisHandler(socketserver.StreamRequestHandler):
    """Line-based text protocol handler with minimal RESP support."""

    def handle(self) -> None:
        while True:
            try:
                request = self._read_request()
            except OSError:
                return
            if request is None:
                return

            command, parts, resp_mode = request
            if command is None:
                try:
                    self._write("-ERR empty command", resp_mode)
                except OSError:
                    return
                continue

            response = self._dispatch(command, parts, resp_mode)
            try:
                self._write(response, resp_mode)
            except OSError:
                return

            if response == "+BYE":
                return

    def _read_request(self) -> tuple[str | None, list[str], bool] | None:
        raw_line = self.rfile.readline()
        if not raw_line:
            return None
        if raw_line.startswith(b"*"):
            try:
                parts = parse_resp(raw_line, self.rfile)
            except RESPError as exc:
                return ("_RESP_ERROR", [str(exc)], True)
            return (parts[0].upper(), parts[1:], True)

        line = raw_line.decode("utf-8").strip()
        if not line:
            return (None, [], False)
        command, *parts = line.split(" ")
        return (command.upper(), parts, False)

    def _dispatch(self, command: str, parts: list[str], resp_mode: bool) -> str:
        if command == "_RESP_ERROR":
            return f"-ERR {parts[0]}"
        if command == "PING":
            return "+PONG"
        if command == "QUIT":
            return "+BYE"
        if command == "SET":
            return self._handle_set(parts, resp_mode)
        if command == "GET":
            return self._handle_get(parts)
        if command == "DEL":
            return self._handle_del(parts)
        if command == "EXISTS":
            return self._handle_exists(parts)
        if command == "HSET":
            return self._handle_hset(parts)
        if command == "HGET":
            return self._handle_hget(parts)
        if command == "HDEL":
            return self._handle_hdel(parts)
        if command == "HGETALL":
            return self._handle_hgetall(parts)
        if command == "SADD":
            return self._handle_sadd(parts)
        if command == "SISMEMBER":
            return self._handle_sismember(parts)
        if command == "SREM":
            return self._handle_srem(parts)
        if command == "SMEMBERS":
            return self._handle_smembers(parts)
        if command == "ZADD":
            return self._handle_zadd(parts)
        if command == "ZRANK":
            return self._handle_zrank(parts)
        if command == "ZRANGE":
            return self._handle_zrange(parts)
        if command == "ZREM":
            return self._handle_zrem(parts)
        if command == "ZPOPMIN":
            return self._handle_zpopmin(parts)
        if command == "ZCARD":
            return self._handle_zcard(parts)
        if command == "EXPIRE":
            return self._handle_expire(parts)
        if command == "EXPIREJITTER":
            return self._handle_expire_jitter(parts)
        if command == "TTL":
            return self._handle_ttl(parts)
        if command == "INCR":
            return self._handle_incr(parts)
        if command == "DECR":
            return self._handle_decr(parts)
        if command == "INCRBY":
            return self._handle_incrby(parts)
        if command == "DECRBY":
            return self._handle_decrby(parts)
        if command == "INVALIDATE":
            return self._handle_invalidate(parts)
        if command == "LOCK":
            return self._handle_lock(parts)
        if command == "UNLOCK":
            return self._handle_unlock(parts)
        if command == "RATECHECK":
            return self._handle_ratecheck(parts)
        return f"-ERR unknown command '{command}'"

    def _handle_set(self, parts: list[str], resp_mode: bool) -> str:
        if len(parts) < 2:
            return "-ERR usage: SET <key> <value>"

        modifier: str | None = None
        if resp_mode:
            if len(parts) > 3:
                return "-ERR usage: SET <key> <value>"
            key = parts[0]
            value = parts[1]
            if len(parts) == 3:
                modifier = parts[2].upper()
        else:
            key = parts[0]
            if len(parts) >= 3 and parts[-1].upper() == "NX":
                modifier = "NX"
                value = " ".join(parts[1:-1])
            else:
                value = " ".join(parts[1:])

        if not value:
            return "-ERR usage: SET <key> <value>"

        if modifier not in {None, "NX"}:
            return "-ERR only NX modifier is supported"

        if modifier == "NX":
            created = self.server.store.setnx(key, value)
            return "+OK" if created else "$nil"

        self.server.store.set(key, value)
        return "+OK"

    def _handle_get(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: GET <key>"
        try:
            value = self.server.store.get(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_del(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: DEL <key>"
        deleted = self.server.store.delete(parts[0])
        return ":1" if deleted else ":0"

    def _handle_exists(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: EXISTS <key>"
        exists = self.server.store.exists(parts[0])
        return ":1" if exists else ":0"

    def _handle_hset(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "-ERR usage: HSET <key> <field> <value>"
        key = parts[0]
        field = parts[1]
        value = " ".join(parts[2:])
        try:
            created = self.server.store.hset(key, field, value)
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{created}"

    def _handle_hget(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: HGET <key> <field>"
        try:
            value = self.server.store.hget(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_hdel(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: HDEL <key> <field>"
        try:
            deleted = self.server.store.hdel(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{deleted}"

    def _handle_hgetall(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: HGETALL <key>"
        try:
            value = self.server.store.hgetall(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_sadd(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: SADD <key> <member>"
        try:
            created = self.server.store.sadd(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{created}"

    def _handle_sismember(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: SISMEMBER <key> <member>"
        try:
            result = self.server.store.sismember(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{result}"

    def _handle_srem(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: SREM <key> <member>"
        try:
            deleted = self.server.store.srem(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{deleted}"

    def _handle_smembers(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: SMEMBERS <key>"
        try:
            value = self.server.store.smembers(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_zadd(self, parts: list[str]) -> str:
        if len(parts) != 3:
            return "-ERR usage: ZADD <key> <score> <member>"
        try:
            score = float(parts[1])
        except ValueError:
            return "-ERR score must be a number"
        try:
            created = self.server.store.zadd(parts[0], score, parts[2])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{created}"

    def _handle_zrank(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: ZRANK <key> <member>"
        try:
            rank = self.server.store.zrank(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{rank}"

    def _handle_zrange(self, parts: list[str]) -> str:
        if len(parts) != 3:
            return "-ERR usage: ZRANGE <key> <start> <stop>"
        try:
            start = int(parts[1])
            stop = int(parts[2])
        except ValueError:
            return "-ERR start and stop must be integers"
        try:
            value = self.server.store.zrange(parts[0], start, stop)
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_zrem(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: ZREM <key> <member>"
        try:
            deleted = self.server.store.zrem(parts[0], parts[1])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{deleted}"

    def _handle_zpopmin(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: ZPOPMIN <key>"
        try:
            value = self.server.store.zpopmin(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        if value is None:
            return "$nil"
        return f"${value}"

    def _handle_zcard(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: ZCARD <key>"
        try:
            count = self.server.store.zcard(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{count}"

    def _handle_expire(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: EXPIRE <key> <seconds>"
        try:
            seconds = int(parts[1])
        except ValueError:
            return "-ERR seconds must be an integer"
        if seconds <= 0:
            return "-ERR seconds must be positive"
        updated = self.server.store.expire(parts[0], seconds)
        return ":1" if updated else ":0"

    def _handle_expire_jitter(self, parts: list[str]) -> str:
        if len(parts) != 3:
            return "-ERR usage: EXPIREJITTER <key> <seconds> <jitter_seconds>"
        try:
            seconds = int(parts[1])
            jitter_seconds = int(parts[2])
        except ValueError:
            return "-ERR seconds and jitter_seconds must be integers"
        if seconds <= 0:
            return "-ERR seconds must be positive"
        if jitter_seconds < 0:
            return "-ERR jitter_seconds must be non-negative"
        applied_ttl = self.server.store.expire_with_jitter(parts[0], seconds, jitter_seconds)
        return f":{applied_ttl}"

    def _handle_ttl(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: TTL <key>"
        ttl_seconds = self.server.store.ttl(parts[0])
        return f":{ttl_seconds}"

    def _handle_incr(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: INCR <key>"
        try:
            value = self.server.store.incr(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{value}"

    def _handle_decr(self, parts: list[str]) -> str:
        if len(parts) != 1:
            return "-ERR usage: DECR <key>"
        try:
            value = self.server.store.decr(parts[0])
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{value}"

    def _handle_incrby(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: INCRBY <key> <amount>"
        try:
            amount = int(parts[1])
        except ValueError:
            return "-ERR amount must be an integer"
        try:
            value = self.server.store.incrby(parts[0], amount)
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{value}"

    def _handle_decrby(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: DECRBY <key> <amount>"
        try:
            amount = int(parts[1])
        except ValueError:
            return "-ERR amount must be an integer"
        if amount < 0:
            return "-ERR amount must be non-negative"
        try:
            value = self.server.store.decrby(parts[0], amount)
        except ValueError as exc:
            return f"-ERR {exc}"
        return f":{value}"

    def _handle_invalidate(self, parts: list[str]) -> str:
        if len(parts) < 1:
            return "-ERR usage: INVALIDATE <key> [reason]"
        key = parts[0]
        reason = " ".join(parts[1:]) if len(parts) > 1 else None
        updated = self.server.store.invalidate(key, reason)
        return ":1" if updated else ":0"

    def _handle_lock(self, parts: list[str]) -> str:
        if len(parts) != 3:
            return "-ERR usage: LOCK <key> <owner> <ttl_seconds>"
        key, owner, ttl_raw = parts
        try:
            ttl_seconds = int(ttl_raw)
        except ValueError:
            return "-ERR ttl_seconds must be an integer"
        if ttl_seconds <= 0:
            return "-ERR ttl_seconds must be positive"
        acquired = self.server.store.acquire_lock(key, owner, ttl_seconds)
        return ":1" if acquired else ":0"

    def _handle_unlock(self, parts: list[str]) -> str:
        if len(parts) != 2:
            return "-ERR usage: UNLOCK <key> <owner>"
        key, owner = parts
        released = self.server.store.release_lock(key, owner)
        return ":1" if released else ":0"

    def _handle_ratecheck(self, parts: list[str]) -> str:
        if len(parts) != 3:
            return "-ERR usage: RATECHECK <key> <limit> <window_seconds>"
        key, limit_raw, window_raw = parts
        try:
            limit = int(limit_raw)
            window_seconds = int(window_raw)
        except ValueError:
            return "-ERR limit and window_seconds must be integers"
        if limit <= 0:
            return "-ERR limit must be positive"
        if window_seconds <= 0:
            return "-ERR window_seconds must be positive"

        result = self.server.store.rate_check(key, limit, window_seconds)
        status = "ALLOWED" if result.allowed else "BLOCKED"
        return (
            f"+{status} remaining={result.remaining} "
            f"reset_in={result.reset_in} count={result.count}"
        )

    def _write(self, response: str, resp_mode: bool) -> None:
        if resp_mode:
            self.wfile.write(encode_text_response(response))
        else:
            self.wfile.write(f"{response}\n".encode("utf-8"))
        self.wfile.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the minimal Mini Redis TCP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--aof-path", default=None)
    parser.add_argument("--sweep-interval", type=float, default=1.0)
    parser.add_argument("--invalidation-grace-seconds", type=int, default=30)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    store = MiniRedisStore(
        aof_path=args.aof_path,
        invalidation_grace_seconds=args.invalidation_grace_seconds,
    )

    with MiniRedisTCPServer(
        (args.host, args.port),
        MiniRedisHandler,
        store=store,
        sweep_interval=args.sweep_interval,
    ) as server:
        print(f"Mini Redis listening on {args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
