import asyncio
import logging.config
import socket
from asyncio import StreamWriter, StreamReader
from contextvars import ContextVar
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
from proxy._log_config import LOGGING_CONFIG
from proxy._proxy_request import ProxyRequest, HTTPScheme
from proxy.connection import Connection
from proxy.endpoint import Endpoint
from proxy.enpoint_type import EndpointType

logging.config.dictConfig(LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)


class ProxyServer:

    def __init__(self, port: int, block_images: bool = False, cfg=None):
        self.connection = ContextVar("connection")
        self.block_images = block_images
        self.HTTP_RESET_MSG = b"HTTP/1.1 403"
        self.port = port
        self._spent_data = {}
        if cfg is not None:
            if isinstance(cfg, dict):
                self._cfg = cfg
            else:
                raise ValueError(f"Config should be {dict.__name__} object")
            for rsc in chain(cfg["limited"], cfg["black-list"]):
                self._spent_data[rsc] = 0
        self.context_token = None
        self.jpg_extensions = {".jpg", ".jpeg", ".png"}

    async def run(self):
        """
        Launch async proxy-server at specified host and port.
        """
        srv = await asyncio.start_server(
            self._handle_connection, LOCALHOST, self.port)

        addr = srv.sockets[0].getsockname()
        LOGGER.info(START_SERVER_MSG.format(app_address=addr))

        async with srv:
            await srv.serve_forever()

    async def _reset_connection(
            self,
            client_writer: StreamWriter,
            pr: ProxyRequest
    ):
        LOGGER.info(f"Blocked image {pr.method:<{len('CONNECT')}} "
                    f"{pr.abs_url}")
        client_writer.write(self.HTTP_RESET_MSG)
        await client_writer.drain()
        client_writer.close()

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
            pr = ProxyRequest(raw_request, self._cfg)
            if self.block_images and pr.is_image_request:
                await self._reset_connection(client_writer, pr)
                return
            LOGGER.info(f"{pr.method:<{len('CONNECT')}} "
                        f"{pr.abs_url}")
            try:
                server_reader, server_writer = await asyncio.open_connection(
                    pr.hostname, pr.port)
            except socket.gaierror:
                LOGGER.info(CONNECTION_REFUSED_MSG.format(
                    method=pr.method, url=pr.abs_url))
                return
            client_endpoint = Endpoint(client_reader, client_writer)
            server_endpoint = Endpoint(server_reader, server_writer)
            self.context_token = self.connection.set(Connection(client_endpoint, server_endpoint, pr))
            if pr.scheme is HTTPScheme.HTTPS:
                await self._handle_https()
            else:
                await self._handle_http()
        except ConnectionResetError:
            LOGGER.info(CONNECTION_CLOSED_MSG.format(url=pr.abs_url))
            if self.context_token is not None:
                self.connection.reset(self.context_token)
        except Exception as e:
            LOGGER.exception(e)
            if self.context_token is not None:
                self.connection.reset(self.context_token)
            asyncio.get_event_loop().stop()

    async def _handle_http(self) -> None:
        """
        Send HTTP request and then forwards the following HTTP requests.
        """
        connection = self.connection.get()
        LOGGER.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=connection.pr.method, url=connection.pr.abs_url)
        )
        await connection.server.write(connection.pr.raw)
        await asyncio.gather(self._forward_to_local(), self._forward_to_remote())

    async def _handle_https(self) -> None:
        """
        Handles https connection by making HTTP tunnel.
        """
        connection = self.connection.get()
        LOGGER.debug(HANDLING_HTTPS_CONNECTION_MSG.format(url=connection.pr.hostname))
        await connection.client.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        LOGGER.debug(CONNECTION_ESTABLISHED_MSG.format(url=connection.pr.abs_url))
        await asyncio.gather(self._forward_to_remote(), self._forward_to_local())

    async def _forward_to_remote(self) -> None:
        """
        Receives data from localhost and forward it to server.
        """
        connection = self.connection.get()
        while True:
            data = await connection.client.read(CHUNK_SIZE)
            if not data:
                await connection.server.close()
                break
            elif self.block_images:
                try:
                    decoded_data = data.decode()
                    if (x in decoded_data for x in self.jpg_extensions):
                        await connection.client.write(self.HTTP_RESET_MSG)
                        await connection.client.close()
                        return
                except UnicodeDecodeError:
                    pass
            await connection.server.write(data)
            self._log_forwarding(EndpointType.SERVER, data)

    async def _forward_to_local(self) -> None:
        """
        Receives data from remote server and forward it to localhost.
        """
        connection = self.connection.get()
        while True:
            data = await connection.server.read(CHUNK_SIZE)
            if connection.pr.restriction:
                if self._spent_data[connection.pr.restriction.initiator] >= \
                        connection.pr.restriction.data_limit:
                    await self._handle_limited_page()
                    break
            if data:
                await connection.client.write(data)
                self._log_forwarding(EndpointType.CLIENT, data)
            else:
                await connection.client.close()
                break
            if connection.pr.restriction:
                self._spent_data[connection.pr.restriction.initiator] += len(data)
                LOGGER.debug(
                    f"{self._spent_data[connection.pr.restriction.initiator]}"
                    f" WAS SPENT FOR {connection.pr.restriction.initiator}"
                )

    async def _handle_limited_page(self) -> None:
        """
        Handles connection for restricted webpage.
        In HTTP case it sends HTML notification page.
        In HTTPS case it closes connection.
        """
        connection = self.connection.get()
        rsc = connection.pr.restriction
        if rsc.data_limit == 0:
            LOGGER.info(BLACK_HOLE_MSG.format(url=rsc.initiator))
        else:
            LOGGER.info(BLOCKED_WEBPAGE.format(url=rsc.initiator))
        if connection.pr.scheme is HTTPScheme.HTTPS:
            msg = "HTTP/1.1 403\r\n\r\n"
        else:
            msg = f"HTTP/1.1 200 OK\r\n\r\n{rsc.http_content}"
        await connection.client.write(msg.encode())
        await connection.client.close()

    def _log_forwarding(self, endpoint_type: EndpointType, data: bytes) -> None:
        """
        Logging forwarding message.
        """
        connection = self.connection.get()
        query = f"{connection.pr.method} {connection.pr.abs_url}"
        if endpoint_type is EndpointType.SERVER:
            sender_ip = connection.server.writer.get_extra_info("peername")[0]
        else:
            sender_ip = connection.client.writer.get_extra_info("peername")[0]
        if sender_ip == "::1":
            pass
        else:
            query = "Response from server"
        LOGGER.debug(f"{sender_ip:<{len('255.255.255.255')}} "
                     f"{query} {len(data)}")
