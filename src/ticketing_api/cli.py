from __future__ import annotations

import argparse

import uvicorn

from ticketing_api.app import create_app
from ticketing_api.settings import Settings


def build_parser() -> argparse.ArgumentParser:
    defaults = Settings.from_env()
    parser = argparse.ArgumentParser(description="Run the ticketing API.")
    parser.add_argument("--host", default=defaults.api_host)
    parser.add_argument("--port", type=int, default=defaults.api_port)
    parser.add_argument("--redis-host", default=defaults.redis_host)
    parser.add_argument("--redis-port", type=int, default=defaults.redis_port)
    parser.add_argument("--hold-ttl", type=int, default=defaults.hold_ttl_seconds)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings(
        api_host=args.host,
        api_port=args.port,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        hold_ttl_seconds=args.hold_ttl,
    )
    uvicorn.run(create_app(settings), host=settings.api_host, port=settings.api_port)
