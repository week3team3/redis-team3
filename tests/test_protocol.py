from __future__ import annotations

import asyncio

import pytest

from mini_redis.protocol import BulkString, ErrorString, SimpleString, encode_command, encode_response, read_frame


@pytest.mark.asyncio
async def test_read_frame_parses_array_of_bulk_strings() -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(b"*3\r\n$3\r\nSET\r\n$5\r\nalpha\r\n$4\r\nbeta\r\n")
    reader.feed_eof()

    frame = await read_frame(reader)

    assert frame == ["SET", "alpha", "beta"]


def test_encode_command_builds_resp_array() -> None:
    payload = encode_command(["PING", "hello"])

    assert payload == b"*2\r\n$4\r\nPING\r\n$5\r\nhello\r\n"


def test_encode_response_handles_common_types() -> None:
    assert encode_response(SimpleString("PONG")) == b"+PONG\r\n"
    assert encode_response(BulkString("value")) == b"$5\r\nvalue\r\n"
    assert encode_response(2) == b":2\r\n"
    assert encode_response(None) == b"$-1\r\n"
    assert encode_response(ErrorString("ERR boom")) == b"-ERR boom\r\n"
