#!/usr/bin/env python3

import asyncio
import socket
from asyncio import StreamWriter, StreamReader
from defaults import HOST, HTTP_PORT
from http_parser import parse, Request


async def handle_client(
        client_reader: StreamReader,
        client_writer: StreamWriter
) -> None:
    raw_request = await client_reader.read(1024)
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
        req: Request
) -> None:
    server_reader, server_writer = await asyncio.open_connection(req.headers["Host"], req.port)
    await asyncio.gather(
        forward(client_reader, server_writer),
        forward(server_reader, client_writer)
    )


async def forward(
        reader: StreamReader,
        writer: StreamWriter
) -> None:
    while True:
        try:
            data = await reader.read(1024)

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
        req: Request
) -> None:
    try:  # weird http urls
        server_reader, server_writer = await asyncio.open_connection(req.headers["Host"], req.port)
    except socket.gaierror:
        print(f"Connection refused: {req.method} {req.url}")
        return
    server_writer.write(req.raw)
    await server_writer.drain()
    await asyncio.gather(
        forward(server_reader, client_writer),
        forward(client_reader, server_writer),
    )


async def run():
    srv = await asyncio.start_server(
        handle_client, HOST, HTTP_PORT)

    addr = srv.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with srv:
        await srv.serve_forever()


if __name__ == '__main__':
    asyncio.run(run())
