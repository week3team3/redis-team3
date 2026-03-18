from __future__ import annotations

import asyncio
from dataclasses import dataclass

CRLF = b"\r\n"


class RespProtocolError(Exception):
    """Raised when a RESP frame is malformed."""


@dataclass(frozen=True)
class SimpleString:
    value: str


@dataclass(frozen=True)
class BulkString:
    value: str


@dataclass(frozen=True)
class ErrorString:
    value: str


RespValue = str | int | None | list["RespValue"] | ErrorString
RespReply = SimpleString | BulkString | int | None | list["RespReply"] | ErrorString


async def _read_line(reader: asyncio.StreamReader) -> bytes:
    try:
        raw = await reader.readuntil(CRLF)
    except asyncio.IncompleteReadError as exc:
        raise RespProtocolError("unexpected end of stream") from exc
    return raw[:-2]


async def read_frame(reader: asyncio.StreamReader) -> RespValue:
    try:
        prefix = await reader.readexactly(1)
    except asyncio.IncompleteReadError as exc:
        raise RespProtocolError("unexpected end of stream") from exc

    if prefix == b"+":
        return (await _read_line(reader)).decode("utf-8")
    if prefix == b"-":
        return ErrorString((await _read_line(reader)).decode("utf-8"))
    if prefix == b":":
        return int((await _read_line(reader)).decode("ascii"))
    if prefix == b"$":
        length = int((await _read_line(reader)).decode("ascii"))
        if length == -1:
            return None
        if length < -1:
            raise RespProtocolError("invalid bulk string length")
        payload = await reader.readexactly(length)
        trailer = await reader.readexactly(2)
        if trailer != CRLF:
            raise RespProtocolError("bulk string missing CRLF")
        return payload.decode("utf-8")
    if prefix == b"*":
        length = int((await _read_line(reader)).decode("ascii"))
        if length == -1:
            return None
        if length < -1:
            raise RespProtocolError("invalid array length")
        items: list[RespValue] = []
        for _ in range(length):
            items.append(await read_frame(reader))
        return items

    raise RespProtocolError(f"unsupported RESP prefix: {prefix!r}")


def encode_command(parts: list[str]) -> bytes:
    encoded = [f"*{len(parts)}\r\n".encode("ascii")]
    for part in parts:
        raw = part.encode("utf-8")
        encoded.append(f"${len(raw)}\r\n".encode("ascii"))
        encoded.append(raw)
        encoded.append(CRLF)
    return b"".join(encoded)


def encode_response(value: RespReply) -> bytes:
    if isinstance(value, SimpleString):
        return b"+" + value.value.encode("utf-8") + CRLF
    if isinstance(value, BulkString):
        raw = value.value.encode("utf-8")
        return b"$" + str(len(raw)).encode("ascii") + CRLF + raw + CRLF
    if isinstance(value, ErrorString):
        return b"-" + value.value.encode("utf-8") + CRLF
    if isinstance(value, int):
        return b":" + str(value).encode("ascii") + CRLF
    if value is None:
        return b"$-1\r\n"
    if isinstance(value, list):
        chunks = [f"*{len(value)}\r\n".encode("ascii")]
        chunks.extend(encode_response(item) for item in value)
        return b"".join(chunks)
    raise TypeError(f"unsupported RESP reply type: {type(value)!r}")
