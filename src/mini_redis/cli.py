from __future__ import annotations

import argparse
import asyncio

from mini_redis.server import MiniRedisServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Mini Redis RESP2 server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6380)
    parser.add_argument("--cleanup-interval", type=float, default=1.0)
    return parser


async def _run_server(args: argparse.Namespace) -> None:
    server = MiniRedisServer(host=args.host, port=args.port, cleanup_interval=args.cleanup_interval)
    await server.start()
    print(f"Mini Redis listening on {args.host}:{args.port}")
    try:
        await server.serve_forever()
    finally:
        await server.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_run_server(args))
    except KeyboardInterrupt:
        pass
