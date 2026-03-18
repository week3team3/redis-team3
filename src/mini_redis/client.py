from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mini_redis.protocol import ErrorString, encode_command, read_frame


class MiniRedisResponseError(RuntimeError):
    """Raised when the server returns a RESP error frame."""


class MiniRedisConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def execute(self, *parts: str) -> str | int | None | list[object]:
        self._writer.write(encode_command(list(parts)))
        await self._writer.drain()
        response = await read_frame(self._reader)
        if isinstance(response, ErrorString):
            raise MiniRedisResponseError(response.value)
        if isinstance(response, list):
            return list(response)
        return response

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


class MiniRedisClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[MiniRedisConnection]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        connection = MiniRedisConnection(reader, writer)
        try:
            yield connection
        finally:
            await connection.close()
