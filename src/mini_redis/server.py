from __future__ import annotations

import asyncio

from mini_redis.engine import CommandEngine, CommandError
from mini_redis.protocol import ErrorString, RespProtocolError, encode_response, read_frame


class MiniRedisServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 6380, cleanup_interval: float = 1.0) -> None:
        self.host = host
        self.port = port
        self.engine = CommandEngine(cleanup_interval=cleanup_interval)
        self._server: asyncio.AbstractServer | None = None

    @property
    def sockets(self) -> list[asyncio.TransportSocket]:
        if self._server is None or self._server.sockets is None:
            return []
        return list(self._server.sockets)

    async def start(self) -> None:
        if self._server is not None:
            return
        await self.engine.start()
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        await self.engine.stop()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while not reader.at_eof():
                try:
                    frame = await read_frame(reader)
                    parts = self._coerce_command(frame)
                    reply = await self.engine.execute(parts)
                except (RespProtocolError, CommandError) as exc:
                    writer.write(encode_response(ErrorString(str(exc))))
                    await writer.drain()
                    continue
                except asyncio.IncompleteReadError:
                    break
                writer.write(encode_response(reply))
                await writer.drain()
        except ConnectionResetError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    def _coerce_command(frame: object) -> list[str]:
        if not isinstance(frame, list):
            raise CommandError("ERR commands must be sent as RESP arrays")
        parts: list[str] = []
        for item in frame:
            if not isinstance(item, str):
                raise CommandError("ERR command arguments must be strings")
            parts.append(item)
        return parts
