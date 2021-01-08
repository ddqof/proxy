import asyncio
import socket
import logging.config
from asyncio import StreamWriter, StreamReader
from itertools import chain

from proxy._defaults import (LOCALHOST,
                             CHUNK_SIZE,
                             CONNECTION_ESTABLISHED_MSG,
                             HANDLING_HTTP_REQUEST_MSG,
                             HANDLING_HTTPS_CONNECTION_MSG,
                             CONNECTION_REFUSED_MSG,
                             START_SERVER_MSG,
                             CONNECTION_CLOSED_MSG,
                             BLOCKED_WEBPAGE,
                             BLACK_HOLE_MSG)
from proxy._request import Request, HTTPScheme
from proxy._log_config import LOGGING_CONFIG


class ProxyServer:

    def __init__(
            self,
            port: int,
            cfg=None
    ):
        self.port = port
        self._spent_data = {}
        if cfg is not None:
            if isinstance(cfg, dict):
                self._cfg = cfg
            else:
                raise ValueError(f"Config should be {dict.__name__} object")
            for rsc in chain(cfg["limited"], cfg["black-list"]):
                self._spent_data[rsc] = 0
        logging.config.dictConfig(LOGGING_CONFIG)
        self._logger = logging.getLogger(__name__)

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
            greeting = Request(raw_request, self._cfg)
            self._logger.info(f"{greeting.method:<{len('CONNECT')}} "
                              f"{greeting.abs_url}")
            try:
                server_reader, server_writer = await asyncio.open_connection(
                    greeting.hostname, greeting.port)
            except socket.gaierror:
                self._logger.info(
                    CONNECTION_REFUSED_MSG.format(
                        method=greeting.method, url=greeting.abs_url))
                return
            args = [
                greeting,
                client_reader,
                client_writer,
                server_reader,
                server_writer
            ]
            if greeting.scheme is HTTPScheme.HTTPS:
                await self._handle_https(*args)
            else:
                await self._handle_http(*args)
        except ConnectionResetError:
            self._logger.info(CONNECTION_CLOSED_MSG.format(
                url=greeting.abs_url)
            )
        except Exception as e:
            self._logger.exception(e)
            asyncio.get_event_loop().stop()

    async def _handle_http(
            self,
            r: Request,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            server_reader: StreamReader,
            server_writer: StreamWriter
    ) -> None:
        """
        Send HTTP request and then forwards the following HTTP requests.
        """
        self._logger.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=r.method, url=r.abs_url)
        )
        server_writer.write(r.raw)
        await server_writer.drain()
        await asyncio.gather(
            self._forward_to_local(server_reader, client_writer, r),
            self._forward_to_remote(client_reader, server_writer, r)
        )

    async def _handle_https(
            self,
            r: Request,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            server_reader: StreamReader,
            server_writer: StreamWriter
    ) -> None:
        """
        Handles https connection by making HTTP tunnel.
        """
        self._logger.debug(
            HANDLING_HTTPS_CONNECTION_MSG.format(url=r.hostname))
        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await client_writer.drain()
        self._logger.debug(CONNECTION_ESTABLISHED_MSG.format(url=r.abs_url))
        await asyncio.gather(
            self._forward_to_remote(client_reader, server_writer, r),
            self._forward_to_local(server_reader, client_writer, r)
        )

    async def _forward_to_remote(
            self,
            local_reader: StreamReader,
            server_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Receives data from localhost and forward it to server.
        """
        while True:
            data = await local_reader.read(CHUNK_SIZE)
            if not data:
                server_writer.close()
                await server_writer.wait_closed()
                break
            server_writer.write(data)
            await server_writer.drain()
            self._log_forwarding(
                server_writer.get_extra_info("peername")[0],
                len(data), r)

    async def _forward_to_local(
            self,
            server_reader: StreamReader,
            local_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Receives data from remote server and forward it to localhost.
        """
        while True:
            data = await server_reader.read(CHUNK_SIZE)
            if r.restriction:
                if self._spent_data[r.restriction.initiator] >= \
                        r.restriction.data_limit:
                    await self._handle_limited_page(local_writer, r)
                    break
            if data:
                local_writer.write(data)
                await local_writer.drain()
                self._log_forwarding(
                    local_writer.get_extra_info("peername")[0],
                    len(data),
                    r)
            else:
                local_writer.close()
                await local_writer.wait_closed()
                break
            if r.restriction:
                self._spent_data[r.restriction.initiator] += len(data)
                self._logger.debug(
                    f"{self._spent_data[r.restriction.initiator]}"
                    f" WAS SPENT FOR {r.restriction.initiator}"
                )

    async def _handle_limited_page(
            self,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handles connection for restricted webpage.
        In HTTP case it sends HTML notification page.
        In HTTPS case it closes connection.
        """
        rsc = r.restriction
        if rsc.data_limit == 0:
            self._logger.info(BLACK_HOLE_MSG.format(url=rsc.initiator))
        else:
            self._logger.info(BLOCKED_WEBPAGE.format(url=rsc.initiator))
        if r.scheme is HTTPScheme.HTTPS:
            msg = "HTTP/1.1 403\r\n\r\n"
        else:
            msg = f"HTTP/1.1 200 OK\r\n\r\n{rsc.http_content}"
        client_writer.write(msg.encode())
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()

    def _log_forwarding(
            self,
            sender_ip: str,
            data_size: int,
            r: Request
    ) -> None:
        """
        Logging forwarding message.
        """
        query = f"{r.method} {r.abs_url}"
        if sender_ip == "::1":
            pass
        else:
            query = "Response from server"
        self._logger.debug(f"{sender_ip:<{len('255.255.255.255')}} "
                           f"{query} {data_size}")
