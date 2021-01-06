import asyncio
import socket
import logging.config

from asyncio import StreamWriter, StreamReader

from proxy._defaults import (LOCALHOST,
                             START_SERVER_MSG,
                             CHUNK_SIZE)
from proxy._config import ProxyConfig
from proxy._log_config import LOGGING_CONFIG
from proxy.flow._flow import Flow
from proxy.connections.greeting import HTTPScheme
from proxy.connections.restricted_connection import RestrictedConnection, Greeting
from proxy.connections.connection import Connection


class ProxyServer:

    def __init__(self, port: int, cfg: dict):
        self.port = port
        self.cfg = ProxyConfig(cfg)
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
            data = await client_reader.read(1024)
            if not data:
                return
            greeting = Greeting(data)
            try:
                server_reader, server_writer = await asyncio.open_connection(
                    greeting.hostname, greeting.port
                )
            except socket.gaierror:
                return
            flow = Flow(
                greeting,
                Connection(client_reader, client_writer),
                Connection(server_reader, server_writer),
                CHUNK_SIZE
            )
            await flow.establish()
            await flow.run()
        except Exception as e:
            self._logger.exception(e)
            asyncio.get_event_loop().stop()
