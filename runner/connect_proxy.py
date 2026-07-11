#!/usr/bin/env python3
"""Fail-closed HTTPS CONNECT proxy listening on a Unix-domain socket."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

type HostSet = frozenset[str]


def parse_arguments(*, arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True, type=Path)
    parser.add_argument("--allowlist", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    return parser.parse_args(args=arguments)


def load_allowlist(*, path: Path) -> HostSet:
    entries = (
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
    )
    return frozenset(entry for entry in entries if entry and not entry.startswith("#"))


def append_event(*, path: Path, event: dict[str, str | int | bool]) -> None:
    record = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        **event,
    }
    with path.open(mode="a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


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


async def read_request_head(*, reader: asyncio.StreamReader) -> tuple[str, list[bytes]]:
    request_line = await reader.readline()
    if not request_line:
        raise ValueError("empty request")
    decoded_line = request_line.decode(encoding="ascii", errors="strict").rstrip("\r\n")
    headers: list[bytes] = []
    total_size = len(request_line)
    while True:
        header = await reader.readline()
        total_size += len(header)
        if total_size > 64 * 1024:
            raise ValueError("proxy request head exceeds 64 KiB")
        if header in {b"\r\n", b"\n", b""}:
            break
        headers.append(header)
    return decoded_line, headers


def parse_connect_target(*, request_line: str) -> tuple[str, int]:
    parts = request_line.split()
    if len(parts) != 3 or parts[0].upper() != "CONNECT":
        raise ValueError("only HTTPS CONNECT is supported")
    authority = parts[1]
    host, separator, port_text = authority.rpartition(":")
    if not separator or not host or not port_text.isdecimal():
        raise ValueError("invalid CONNECT authority")
    port = int(port_text)
    if port != 443:
        raise ValueError("only destination port 443 is allowed")
    return host.lower().rstrip("."), port


async def handle_client(
    *,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    allowed_hosts: HostSet,
    log_path: Path,
) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    host = ""
    try:
        request_line, _headers = await read_request_head(reader=reader)
        host, port = parse_connect_target(request_line=request_line)
        allowed = host in allowed_hosts
        append_event(
            path=log_path,
            event={"event": "connect", "host": host, "port": port, "allowed": allowed},
        )
        if not allowed:
            writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            await writer.drain()
            return
        upstream_reader, upstream_writer = await asyncio.open_connection(host=host, port=port)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(
            relay(reader=reader, writer=upstream_writer),
            relay(reader=upstream_reader, writer=writer),
        )
    except (ConnectionError, OSError, UnicodeError, ValueError) as error:
        append_event(
            path=log_path,
            event={
                "event": "proxy_error",
                "host": host,
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        if not writer.is_closing():
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            await writer.drain()
    finally:
        if upstream_writer is not None and not upstream_writer.is_closing():
            await close_writer(writer=upstream_writer)
        if not writer.is_closing():
            await close_writer(writer=writer)


async def run_proxy(*, socket_path: Path, allowlist_path: Path, log_path: Path) -> None:
    allowed_hosts = load_allowlist(path=allowlist_path)
    socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    server = await asyncio.start_unix_server(
        client_connected_cb=lambda reader, writer: asyncio.create_task(
            handle_client(
                reader=reader,
                writer=writer,
                allowed_hosts=allowed_hosts,
                log_path=log_path,
            )
        ),
        path=socket_path,
    )
    socket_path.chmod(mode=0o600)
    append_event(
        path=log_path,
        event={"event": "proxy_ready", "allowed_host_count": len(allowed_hosts)},
    )
    async with server:
        await server.serve_forever()


def main() -> None:
    arguments = parse_arguments()
    asyncio.run(
        run_proxy(
            socket_path=arguments.socket,
            allowlist_path=arguments.allowlist,
            log_path=arguments.log,
        )
    )


if __name__ == "__main__":
    main()

