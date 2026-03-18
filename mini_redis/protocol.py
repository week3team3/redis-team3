from __future__ import annotations

from typing import BinaryIO


class RESPError(ValueError):
    pass


def parse_resp(first_line: bytes, reader: BinaryIO) -> list[str]:
    if not first_line.startswith(b"*"):
        raise RESPError("RESP array expected")
    if not first_line.endswith(b"\r\n"):
        raise RESPError("malformed RESP header")

    try:
        count = int(first_line[1:-2].decode("ascii"))
    except ValueError as exc:
        raise RESPError("invalid RESP array length") from exc

    if count <= 0:
        raise RESPError("RESP array must contain at least one item")

    parts: list[str] = []
    for _ in range(count):
        prefix = reader.read(1)
        if prefix != b"$":
            raise RESPError("only RESP bulk strings are supported")

        length_line = reader.readline()
        if not length_line.endswith(b"\r\n"):
            raise RESPError("malformed RESP bulk length")

        try:
            length = int(length_line[:-2].decode("ascii"))
        except ValueError as exc:
            raise RESPError("invalid RESP bulk length") from exc

        if length < 0:
            raise RESPError("null bulk strings are not supported in requests")

        payload = reader.read(length)
        if len(payload) != length:
            raise RESPError("unexpected EOF while reading RESP bulk string")

        suffix = reader.read(2)
        if suffix != b"\r\n":
            raise RESPError("malformed RESP bulk string terminator")

        parts.append(payload.decode("utf-8"))

    return parts


def encode_text_response(response: str) -> bytes:
    if response.startswith("+"):
        return f"{response}\r\n".encode("utf-8")
    if response.startswith("-"):
        return f"{response}\r\n".encode("utf-8")
    if response == "$nil":
        return b"$-1\r\n"
    if response.startswith("$"):
        payload = response[1:].encode("utf-8")
        return f"${len(payload)}\r\n".encode("ascii") + payload + b"\r\n"
    if response.startswith(":"):
        return f"{response}\r\n".encode("utf-8")
    return f"-ERR unsupported response '{response}'\r\n".encode("utf-8")
