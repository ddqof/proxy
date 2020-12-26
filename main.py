#!/usr/bin/env python3

import asyncio
import sys
import socket
import logging.config
from asyncio import StreamWriter, StreamReader
from _arg_parser import parse_args
from _defaults import (LOCALHOST,
                       CHUNK_SIZE,
                       CONNECTION_ESTABLISHED_MSG,
                       HANDLING_HTTP_REQUEST_MSG,
                       HANDLING_HTTPS_CONNECTION_MSG,
                       CONNECTION_REFUSED_MSG,
                       START_SERVER_MSG,
                       CONNECTION_CLOSED_MSG)
from _http_parser import parse, Request
from log_config import LOGGING_CONFIG


class ProxyServer:

    def __init__(self, port: int):
        logging.config.dictConfig(LOGGING_CONFIG)
        self._logger = logging.getLogger(__name__)
        self.port = port
        self._spent_data_amount = {}

    async def run(self):
        """
        Launch async proxy-server at specified host and port.
        """
        srv = await asyncio.start_server(
            self._handle_connection, LOCALHOST, self.port)

        addr = srv.sockets[0].getsockname()
        self._logger.info(START_SERVER_MSG.format(app_address=addr))

        async with srv:
            await srv.serve_forever()

    async def _handle_connection(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter
    ) -> None:
        """
        Handle every client response.
        Called whenever a new connection is established.
        """
        try:
            raw_request = await client_reader.read(CHUNK_SIZE)
            await client_writer.drain()
            if not raw_request:
                return
            request = parse(raw_request)
            self._logger.info(f"{request.method:<{len('CONNECT')}} {request.url}")
            if request.method == "CONNECT":
                await self._handle_https(client_reader, client_writer, request)
            else:
                await self._handle_http(client_reader, client_writer, request)
        except Exception as e:
            self._logger.exception(e)

    async def _handle_https(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handle https connection by making HTTP tunnel.
        """
        self._logger.debug(HANDLING_HTTPS_CONNECTION_MSG.format(url=r.host))
        server_reader, server_writer = await asyncio.open_connection(r.host, r.port)
        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self._logger.debug(CONNECTION_ESTABLISHED_MSG.format(url=r.url))
        await asyncio.gather(
            self._forward(client_reader, server_writer, r),
            self._forward(server_reader, client_writer, r)
        )

    def _log_forwarding(
            self,
            sender_ip: str,
            data_size: int,
            r: Request
    ) -> None:
        if sender_ip == "::1":
            query = f"{r.method} {r.url}"
        else:
            query = "Response from server"
        self._logger.debug(f"{sender_ip} {query} {data_size}")

    async def _forward(
            self,
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
                    self._log_forwarding(
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
                self._logger.info(CONNECTION_CLOSED_MSG.format(url=r.url))
                break

    async def _handle_http(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handle http connection by forwarding not modified HTTP requests.
        """
        self._logger.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=r.method, url=r.url)
        )
        try:  # weird http urls
            server_reader, server_writer = await asyncio.open_connection(r.host, r.port)
        except socket.gaierror:
            self._logger.info(
                CONNECTION_REFUSED_MSG.format(
                    method=r.method, url=r.url)
            )
            return
        server_writer.write(r.raw)
        await server_writer.drain()
        await asyncio.gather(
            self._forward(server_reader, client_writer, r),
            self._forward(client_reader, server_writer, r)
        )


if __name__ == '__main__':
    args = parse_args()
    proxy = ProxyServer(args.port)
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        sys.exit(1)
