#!/usr/bin/env python3
"""Bridge a namespace-local TCP proxy port to a host Unix-domain socket."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path


def parse_arguments(*, arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=18080, type=int)
    parser.add_argument("--ready-file", required=True, type=Path)
    return parser.parse_args(args=arguments)


async def close_writer(*, writer: asyncio.StreamWriter) -> None:
    writer.close()
    await writer.wait_closed()


async def relay(
    *,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    while data := await reader.read(64 * 1024):
        writer.write(data)
        await writer.drain()
    if writer.can_write_eof():
        writer.write_eof()


async def handle_client(
    *,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    socket_path: Path,
) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        upstream_reader, upstream_writer = await asyncio.open_unix_connection(
            path=socket_path
        )
        await asyncio.gather(
            relay(reader=reader, writer=upstream_writer),
            relay(reader=upstream_reader, writer=writer),
        )
    except (ConnectionError, OSError):
        if not writer.is_closing():
            writer.close()
    finally:
        if upstream_writer is not None and not upstream_writer.is_closing():
            await close_writer(writer=upstream_writer)
        if not writer.is_closing():
            await close_writer(writer=writer)


async def run_bridge(
    *,
    socket_path: Path,
    host: str,
    port: int,
    ready_file: Path,
) -> None:
    server = await asyncio.start_server(
        client_connected_cb=lambda reader, writer: asyncio.create_task(
            handle_client(reader=reader, writer=writer, socket_path=socket_path)
        ),
        host=host,
        port=port,
    )
    ready_file.write_text("ready\n", encoding="utf-8")
    async with server:
        await server.serve_forever()


def main() -> None:
    arguments = parse_arguments()
    asyncio.run(
        run_bridge(
            socket_path=arguments.socket,
            host=arguments.host,
            port=arguments.port,
            ready_file=arguments.ready_file,
        )
    )


if __name__ == "__main__":
    main()

