import asyncio
import re
import socket
import logging.config
from asyncio import StreamWriter, StreamReader
from proxy.config_handler import RestrictedResource
from typing import List
from proxy._defaults import (LOCALHOST,
                             CHUNK_SIZE,
                             CONNECTION_ESTABLISHED_MSG,
                             HANDLING_HTTP_REQUEST_MSG,
                             HANDLING_HTTPS_CONNECTION_MSG,
                             CONNECTION_REFUSED_MSG,
                             START_SERVER_MSG,
                             CONNECTION_CLOSED_MSG,
                             DATA_LIMIT_PATH,
                             BLACK_HOLE_PATH,
                             BLOCKED_WEBPAGE,
                             BLACK_HOLE_MSG)
from proxy._http_parser import parse, Request
from proxy._log_config import LOGGING_CONFIG


class ProxyServer:

    def __init__(
            self,
            port: int,
            restricted: List[RestrictedResource] = None,
            black_list: List[str] = None,
    ):
        if restricted is None:
            restricted = []
        if black_list is None:
            black_list = []
        self.port = port
        self._restricted = restricted
        self._spent_data_amount = {}
        logging.config.dictConfig(LOGGING_CONFIG)
        self._logger = logging.getLogger(__name__)
        self._black_list = black_list

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
            if any(link in request.host_url
                   for link in self._black_list):
                await self._handle_black_list(client_writer, request)
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

    async def _handle_black_list(
            self,
            writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handles connection for blocked webpage.
        In HTTP case it sends HTML notification banner.
        In HTTPS case it sends not 200 status code that
        raises client error.
        """
        if r.method == "CONNECT":
            message = "HTTP/1.1 500\r\n\r\n"
        else:
            with open(BLACK_HOLE_PATH) as f:
                message = f"HTTP/1.1 OK\r\n\r\n{f.read()}"
        self._logger.info(BLACK_HOLE_MSG.format(url=r.host_url))
        writer.write(message.encode())
        await writer.drain()
        writer.close()

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
                is_data_lim_reached = self._is_data_lim_reached(r.host_url)
                if is_data_lim_reached:
                    await self._handle_limited_page(localhost_writer, r)
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
                        self._save_traffic_amount(r.host_url, len(data))
                    else:
                        localhost_writer.close()
                        await localhost_writer.wait_closed()
                        break
        except ConnectionResetError:
            self._logger.info(CONNECTION_CLOSED_MSG.format(url=r.abs_url))

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
        self._logger.info(BLOCKED_WEBPAGE.format(url=r.host_url))
        if r.method == "CONNECT":
            client_writer.close()
            await client_writer.wait_closed()
        else:
            with open(DATA_LIMIT_PATH) as f:
                client_writer.write(
                    f"HTTP/1.1 200 OK\r\n\r\n{f.read()}".encode()
                )
            await client_writer.drain()
            client_writer.close()
            await client_writer.wait_closed()

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

    def _is_data_lim_reached(
            self,
            resource_link: str
    ) -> bool:
        """
        Check if data limit is reached for particular resource.
        Used for control traffic from restricted resources.
        """
        for rsc in self._restricted:
            if any(re.search(pattern, resource_link) for
                   pattern in rsc.url_patterns) or \
                    rsc.host_url in resource_link:
                try:
                    return self._spent_data_amount[rsc.host_url] > \
                           rsc.data_limit
                except KeyError:
                    return False

    def _save_traffic_amount(
            self,
            resource_link: str,
            chunk_size: int
    ) -> None:
        """
        Save spent traffic amount for providing control of
        restricted resources.
        """
        for rsc in self._restricted:
            if any(re.search(pattern, resource_link) for
                   pattern in rsc.url_patterns) or \
                    rsc.host_url in resource_link:
                #  don't use rsc.host_url == r.host_url
                #  because r.host_url can contain extra www
                try:
                    self._spent_data_amount[rsc.host_url] += chunk_size
                except KeyError:
                    self._spent_data_amount[rsc.host_url] = chunk_size
                self._logger.debug(f"{self._spent_data_amount[rsc.host_url]}"
                                   f" WAS SPENT FOR {rsc.host_url}")
