import asyncio
import logging.config
import socket
from asyncio import StreamWriter, StreamReader
from contextvars import ContextVar
from itertools import chain

from proxy._connection import CHUNK_SIZE
from proxy._connection import Connection
from proxy._defaults import (LOCALHOST,
                             CONNECTION_ESTABLISHED_MSG,
                             HANDLING_HTTP_REQUEST_MSG,
                             HANDLING_HTTPS_CONNECTION_MSG,
                             CONNECTION_REFUSED_MSG,
                             START_SERVER_MSG,
                             CONNECTION_CLOSED_MSG)
from proxy._endpoint import Endpoint
from proxy._log_config import LOGGING_CONFIG
from proxy._proxy_request import ProxyRequest, HTTPScheme

logging.config.dictConfig(LOGGING_CONFIG)
LOGGER = logging.getLogger(__name__)

CONNECTION_ESTABLISHED_HTTP_MSG = b"HTTP/1.1 200 Connection established\r\n\r\n"


class ProxyServer:

    def __init__(self, port: int = 8080, block_images: bool = False, cfg=None):
        self.connection = ContextVar("connection")
        self.block_images = block_images
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
            print(raw_request)
            await client_writer.drain()
            if not raw_request:
                return
            pr = ProxyRequest(raw_request, self._cfg)
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
            connection = Connection(client_endpoint, server_endpoint, pr, self.block_images)
            self.context_token = self.connection.set(connection)
            if self.block_images and pr.is_image_request:
                await self.connection.get().reset()
                return
            if pr.scheme is HTTPScheme.HTTPS:
                await self._handle_https()
            else:
                await self._handle_http()
        except Exception as e:
            if isinstance(e, ConnectionResetError):
                LOGGER.info(CONNECTION_CLOSED_MSG.format(url=pr.abs_url))
            else:
                LOGGER.exception(e)
                asyncio.get_event_loop().stop()
            if self.context_token is not None:
                self.connection.reset(self.context_token)

    async def _handle_http(self) -> None:
        """
        Send HTTP request and then forwards the following HTTP requests.
        """
        connection = self.connection.get()
        LOGGER.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=connection.pr.method, url=connection.pr.abs_url)
        )
        await connection.server.write_and_drain(connection.pr.raw)
        await asyncio.gather(connection.forward_to_client(self._spent_data), connection.forward_to_server())

    async def _handle_https(self) -> None:
        """
        Handles https connection by making HTTP tunnel.
        """
        connection = self.connection.get()
        LOGGER.debug(HANDLING_HTTPS_CONNECTION_MSG.format(url=connection.pr.hostname))
        restriction = connection.pr.restriction
        if restriction:
            if self._spent_data[restriction.initiator] >= restriction.data_limit:
                await connection.reset()
                return
        await connection.client.write_and_drain(CONNECTION_ESTABLISHED_HTTP_MSG)
        LOGGER.debug(CONNECTION_ESTABLISHED_MSG.format(url=connection.pr.abs_url))
        await asyncio.gather(connection.forward_to_server(), connection.forward_to_client(self._spent_data))
