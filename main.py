#!/usr/bin/env python3

import asyncio
import socket
import logging.config
from asyncio import StreamWriter, StreamReader
from _arg_parser import parse_args
from _defaults import (
    LOCALHOST,
    CHUNK_SIZE,
    CONNECTION_ESTABLISHED_MSG,
    HANDLING_HTTP_REQUEST_MSG,
    HANDLING_HTTPS_CONNECTION_MSG,
    CONNECTION_REFUSED_MSG,
    START_SERVER_MSG,
    CONNECTION_CLOSED_MSG,
)
from _http_parser import parse, Request
from log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


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
    logger.info(f"{request.method:<{len('CONNECT')}} {request.url}")
    if request.method == "CONNECT":
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
    logger.debug(HANDLING_HTTPS_CONNECTION_MSG.format(url=r.headers["Host"]))
    server_reader, server_writer = await asyncio.open_connection(
        r.headers["Host"], r.port
    )
    client_writer.write(b"HTTP/1.1 200\r\n\r\n")
    logger.debug(CONNECTION_ESTABLISHED_MSG.format(url=r.url))
    await asyncio.gather(
        forward(client_reader, server_writer, r),
        forward(server_reader, client_writer, r)
    )


def log_forwarding(
        sender_ip: str,
        data_size: int,
        r: Request
) -> None:
    if sender_ip == "::1":
        query = f"{r.method} {r.url}"
    else:
        query = "Response from server"
    logger.debug(f"{sender_ip} {query} {data_size}")


async def forward(
        reader: StreamReader,
        writer: StreamWriter,
        r: Request
) -> None:
    """
    Forwarding HTTP requests between reader and writer until
    reader doesn't close connection or send empty request.
    """
    while True:
        try:
            data = await reader.read(CHUNK_SIZE)
            if data:
                log_forwarding(
                    writer.get_extra_info("peername")[0],
                    len(data),
                    r
                )
            else:
                writer.close()
                await writer.wait_closed()
                break

            writer.write(data)
            await writer.drain()
        except ConnectionResetError:
            logger.info(CONNECTION_CLOSED_MSG.format(url=r.url))
            break


async def handle_http(
        client_reader: StreamReader,
        client_writer: StreamWriter,
        r: Request
) -> None:
    """
    Handle http connection by forwarding not modified HTTP requests.
    """
    logger.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=r.method, url=r.url
        )
    )
    try:  # weird http urls
        server_reader, server_writer = await asyncio.open_connection(
            r.headers["Host"], r.port
        )
    except socket.gaierror:
        logger.info(
            CONNECTION_REFUSED_MSG.format(
                method=r.method, url=r.url
            )
        )
        return
    server_writer.write(r.raw)
    await server_writer.drain()
    await asyncio.gather(
        forward(server_reader, client_writer, r),
        forward(client_reader, server_writer, r)
    )


async def start(port: int):
    """
    Launch async proxy-server at specified host and port.
    """
    srv = await asyncio.start_server(
        handle_connection, LOCALHOST, port)

    addr = srv.sockets[0].getsockname()
    logger.info(START_SERVER_MSG.format(app_address=addr))

    async with srv:
        await srv.serve_forever()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(start(args.port))
