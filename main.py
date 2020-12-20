#!/usr/bin/env python3

import asyncio
import socket
from asyncio import StreamWriter, StreamReader
from arg_parser import parse_args
from defaults import LOCALHOST, CHUNK_SIZE, DEF_PORT
from http_parser import parse, Request


async def handle_connection(
        client_reader: StreamReader,
        client_writer: StreamWriter
) -> None:
    """
    Handle every client response.
    Called whenever a new connection is established.
    """
    raw_request = await client_reader.read(CHUNK_SIZE)
    await client_writer.drain()
    if not raw_request:
        return
    request = parse(raw_request)
    if request.method == "CONNECT":
        client_writer.write(b"HTTP/1.1 200\r\n\r\n")
        await handle_https(client_reader, client_writer, request)
    else:
        await handle_http(client_reader, client_writer, request)


async def handle_https(
        client_reader: StreamReader,
        client_writer: StreamWriter,
        r: Request
) -> None:
    """
    Handle https connection by making HTTP tunnel.
    """
    server_reader, server_writer = await asyncio.open_connection(
        r.headers["Host"], r.port
    )
    await asyncio.gather(
        forward(client_reader, server_writer),
        forward(server_reader, client_writer)
    )


async def forward(
        reader: StreamReader,
        writer: StreamWriter
) -> None:
    """
    Forwarding HTTP requests between reader and writer until
    reader doesn't close connection or send empty request.
    """
    while True:
        try:
            data = await reader.read(CHUNK_SIZE)

            if not data:
                writer.close()
                await writer.wait_closed()
                break

            writer.write(data)
            await writer.drain()
        except ConnectionResetError:
            print("Connection closed")
            break


async def handle_http(
        client_reader: StreamReader,
        client_writer: StreamWriter,
        r: Request
) -> None:
    """
    Handle http connection by forwarding not modified HTTP requests.
    """
    try:  # weird http urls
        server_reader, server_writer = await asyncio.open_connection(
            r.headers["Host"], r.port
        )
    except socket.gaierror:
        print(f"Connection refused: {r.method} {r.url}")
        return
    server_writer.write(r.raw)
    await server_writer.drain()
    await asyncio.gather(
        forward(server_reader, client_writer),
        forward(client_reader, server_writer),
    )


async def run(port: int):
    """
    Launch async proxy at specified host and port.
    """
    srv = await asyncio.start_server(
        handle_connection, LOCALHOST, port)

    addr = srv.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with srv:
        await srv.serve_forever()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(run(args.port))
