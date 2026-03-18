from __future__ import annotations

import asyncio
from dataclasses import dataclass

from mini_redis.protocol import BulkString, RespReply, SimpleString
from mini_redis.store import RedisStore


class CommandError(Exception):
    """Raised when a command is invalid."""


@dataclass
class _CommandRequest:
    parts: list[str] | None
    future: asyncio.Future[RespReply] | None = None


class CommandEngine:
    def __init__(self, store: RedisStore | None = None, cleanup_interval: float = 1.0) -> None:
        self.store = store or RedisStore()
        self.cleanup_interval = cleanup_interval
        self._queue: asyncio.Queue[_CommandRequest] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._cleanup_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._run(), name="mini-redis-worker")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name="mini-redis-cleanup")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        await self._queue.put(_CommandRequest(parts=None))
        if self._worker_task is not None:
            await self._worker_task
            self._worker_task = None

    async def execute(self, parts: list[str]) -> RespReply:
        if not self._running:
            raise RuntimeError("command engine is not running")
        future: asyncio.Future[RespReply] = asyncio.get_running_loop().create_future()
        await self._queue.put(_CommandRequest(parts=parts, future=future))
        return await future

    async def _run(self) -> None:
        while True:
            request = await self._queue.get()
            if request.parts is None:
                return
            if request.parts == ["__CLEANUP__"]:
                self.store.cleanup_expired()
                if request.future is not None and not request.future.done():
                    request.future.set_result(SimpleString("OK"))
                continue
            if request.future is None:
                continue
            try:
                result = self._dispatch(request.parts)
            except Exception as exc:
                request.future.set_exception(exc)
            else:
                request.future.set_result(result)

    async def _cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.cleanup_interval)
            if not self._running:
                break
            await self._queue.put(_CommandRequest(parts=["__CLEANUP__"]))

    def _dispatch(self, parts: list[str]) -> RespReply:
        if not parts:
            raise CommandError("ERR empty command")

        command = parts[0].upper()
        args = parts[1:]

        if command == "PING":
            self._require_arity(command, args, minimum=0, maximum=1)
            return SimpleString(args[0] if args else "PONG")

        if command == "SET":
            self._require_arity(command, args, minimum=2)
            key, value = args[0], args[1]
            nx, ex = self._parse_set_options(args[2:])
            was_set = self.store.set(key, value, nx=nx, ex=ex)
            if not was_set and nx:
                return None
            return SimpleString("OK")

        if command == "GET":
            self._require_arity(command, args, expected=1)
            value = self.store.get(args[0])
            return None if value is None else BulkString(value)

        if command == "DEL":
            self._require_arity(command, args, minimum=1)
            return self.store.delete(*args)

        if command == "EXPIRE":
            self._require_arity(command, args, expected=2)
            seconds = self._parse_int(args[1], "ERR invalid expire time")
            return self.store.expire(args[0], seconds)

        if command == "TTL":
            self._require_arity(command, args, expected=1)
            return self.store.ttl(args[0])

        if command == "EXISTS":
            self._require_arity(command, args, minimum=1)
            return self.store.exists(*args)

        if command == "SETIFEQ":
            self._require_arity(command, args, expected=3)
            return 1 if self.store.set_if_eq(args[0], args[1], args[2]) else 0

        if command == "DELIFEQ":
            self._require_arity(command, args, expected=2)
            return 1 if self.store.del_if_eq(args[0], args[1]) else 0

        raise CommandError(f"ERR unknown command '{command}'")

    @staticmethod
    def _require_arity(
        command: str,
        args: list[str],
        *,
        expected: int | None = None,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> None:
        size = len(args)
        if expected is not None and size != expected:
            raise CommandError(f"ERR wrong number of arguments for '{command}' command")
        if minimum is not None and size < minimum:
            raise CommandError(f"ERR wrong number of arguments for '{command}' command")
        if maximum is not None and size > maximum:
            raise CommandError(f"ERR wrong number of arguments for '{command}' command")

    def _parse_set_options(self, options: list[str]) -> tuple[bool, int | None]:
        nx = False
        ex: int | None = None
        index = 0

        while index < len(options):
            option = options[index].upper()
            if option == "NX":
                if nx:
                    raise CommandError("ERR duplicate NX option")
                nx = True
                index += 1
                continue
            if option == "EX":
                if ex is not None:
                    raise CommandError("ERR duplicate EX option")
                if index + 1 >= len(options):
                    raise CommandError("ERR syntax error")
                ex = self._parse_positive_int(options[index + 1], "ERR invalid expire time")
                index += 2
                continue
            raise CommandError("ERR syntax error")

        return nx, ex

    @staticmethod
    def _parse_int(raw: str, error_message: str) -> int:
        try:
            return int(raw)
        except ValueError as exc:
            raise CommandError(error_message) from exc

    def _parse_positive_int(self, raw: str, error_message: str) -> int:
        value = self._parse_int(raw, error_message)
        if value <= 0:
            raise CommandError(error_message)
        return value
