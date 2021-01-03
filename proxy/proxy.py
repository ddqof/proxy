import asyncio
import socket
import logging.config

from asyncio import StreamWriter, StreamReader
from proxy._defaults import (LOCALHOST,
                             CHUNK_SIZE,
                             CONNECTION_ESTABLISHED_MSG,
                             HANDLING_HTTP_REQUEST_MSG,
                             HANDLING_HTTPS_CONNECTION_MSG,
                             CONNECTION_REFUSED_MSG,
                             START_SERVER_MSG,
                             CONNECTION_CLOSED_MSG,
                             BLOCKED_WEBPAGE,
                             BLACK_HOLE_MSG,
                             BLACK_HOLE_PATH,
                             DATA_LIMIT_PATH)
from proxy._config_handler import (restricted_list_from_cfg,
                                   black_list_from_cfg)
from proxy._bad_responder import BadResponder
from proxy._observer import Observer
from proxy._http_parser import parse, Request
from proxy._log_config import LOGGING_CONFIG


class ProxyServer:

    def __init__(self, port: int):
        self.port = port
        self._observer = Observer(
            restricted=restricted_list_from_cfg(),
            black_list=black_list_from_cfg()
        )
        self._responder = BadResponder(BLACK_HOLE_PATH, DATA_LIMIT_PATH)
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
            request = parse(raw_request)
            self._logger.info(f"{request.method:<{len('CONNECT')}} "
                              f"{request.abs_url}")
            if self._observer.is_link_in_black_list(request.host_url):
                await self._responder.send_black_list_response(
                    client_writer, request
                )
                self._logger.info(BLACK_HOLE_MSG.format(url=request.host_url))
            else:
                if request.method == "CONNECT":
                    await self._handle_https(
                        client_reader, client_writer, request
                    )
                else:
                    await self._handle_http(
                        client_reader, client_writer, request
                    )
        except Exception as e:
            self._logger.exception(e)
            asyncio.get_event_loop().stop()

    async def _handle_http(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Send HTTP request and then forwards the following HTTP requests.
        """
        self._logger.debug(HANDLING_HTTP_REQUEST_MSG.format(
            method=r.method, url=r.abs_url)
        )
        try:  # weird http urls
            server_reader, server_writer = await asyncio.open_connection(
                r.host_url, r.port
            )
        except socket.gaierror:
            self._logger.info(
                CONNECTION_REFUSED_MSG.format(method=r.method, url=r.abs_url)
            )
            return
        server_writer.write(r.raw)
        await server_writer.drain()
        await asyncio.gather(
            self._forward_to_local(server_reader, client_writer, r),
            self._forward_to_remote(client_reader, server_writer, r)
        )

    async def _forward_to_remote(
            self,
            localhost_reader: StreamReader,
            server_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Receives data from localhost and forward it to server.
        """
        try:
            while True:
                data = await localhost_reader.read(CHUNK_SIZE)
                if not data:
                    server_writer.close()
                    await server_writer.wait_closed()
                    break
                server_writer.write(data)
                await server_writer.drain()
                self._log_forwarding(
                    server_writer.get_extra_info("peername")[0],
                    len(data),
                    r
                )
        except ConnectionResetError:
            self._logger.info(CONNECTION_CLOSED_MSG.format(url=r.abs_url))

    async def _forward_to_local(
            self,
            server_reader: StreamReader,
            localhost_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Receives data from remote server and forward it to localhost.
        """
        try:
            while True:
                data = await server_reader.read(CHUNK_SIZE)
                if self._observer.is_data_lim_reached(r.host_url) and data:
                    #  second condition for data required for not to
                    #  join response from remote server and response
                    #  from proxy that page is limited
                    self._logger.info(BLOCKED_WEBPAGE.format(url=r.host_url))
                    await self._responder.send_limited_page_response(
                        localhost_writer, r
                    )
                    break
                else:
                    if data:
                        localhost_writer.write(data)
                        await localhost_writer.drain()
                        self._log_forwarding(
                            localhost_writer.get_extra_info("peername")[0],
                            len(data),
                            r
                        )
                        update_info = self._observer.update_state(
                            r.host_url, len(data)
                        )
                        if update_info is not None:
                            self._logger.info(update_info)
                    else:
                        localhost_writer.close()
                        await localhost_writer.wait_closed()
                        break
        except ConnectionResetError:
            self._logger.info(CONNECTION_CLOSED_MSG.format(url=r.abs_url))

    async def _handle_https(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handles https connection by making HTTP tunnel.
        """
        self._logger.debug(
            HANDLING_HTTPS_CONNECTION_MSG.format(url=r.host_url))
        server_reader, server_writer = await asyncio.open_connection(
            r.host_url, r.port
        )
        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self._logger.debug(CONNECTION_ESTABLISHED_MSG.format(url=r.abs_url))
        await asyncio.gather(
            self._forward_to_remote(client_reader, server_writer, r),
            self._forward_to_local(server_reader, client_writer, r)
        )

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
