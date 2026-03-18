from __future__ import annotations

import argparse
import socket
from typing import Iterable


def send_command(host: str, port: int, command: str, timeout: float = 2.0) -> str:
    with socket.create_connection((host, port), timeout=timeout) as client:
        client.sendall(f"{command}\n".encode("utf-8"))
        data = client.recv(4096)
    return data.decode("utf-8").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive CLI for PyMiniRedis.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def run_interactive_cli(host: str, port: int, timeout: float) -> int:
    with socket.create_connection((host, port), timeout=timeout) as client:
        reader = client.makefile("r", encoding="utf-8", newline="\n")
        writer = client.makefile("w", encoding="utf-8", newline="\n")

        prompt = f"{host}:{port}> "
        while True:
            try:
                raw_command = input(prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            command = raw_command.strip()
            if not command:
                continue

            if command.lower() in {"exit", "quit"}:
                writer.write("QUIT\n")
                writer.flush()
                response = reader.readline().strip()
                if response:
                    print(response)
                break

            writer.write(f"{command}\n")
            writer.flush()
            response = reader.readline().strip()
            print(response)

    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command:
        command = " ".join(args.command).strip()
        if not command:
            return 0
        print(send_command(args.host, args.port, command, args.timeout))
        return 0

    return run_interactive_cli(args.host, args.port, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
