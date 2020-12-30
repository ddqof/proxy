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
                             BLACK_HOLE_PATH)
from proxy._http_parser import parse, Request
from proxy._log_config import LOGGING_CONFIG


class ProxyServer:

    def __init__(
            self,
            port: int,
            restricted: List[RestrictedResource] = None,
            black_list: List[str] = None
    ):
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
            await self._handle_black_list(client_writer, request)
            if request.method == "CONNECT":
                await self._handle_https(client_reader, client_writer, request)
            else:
                await self._handle_http(client_reader, client_writer, request)
        except Exception as e:
            self._logger.exception(e)

    async def _handle_black_list(
            self,
            writer: StreamWriter,
            r: Request
    ) -> None:
        if any(
                link in r.host_url
                for link in self._black_list
        ):
            if r.method == "CONNECT":
                message = "HTTP/1.1 500\r\n\r\n"
            else:
                with open(BLACK_HOLE_PATH) as f:
                    message = f"HTTP/1.1 OK\r\n\r\n{f.read()}"
            self._logger.info(f"Black Hole: {r.method} {r.host_url}")
            writer.write(message.encode())
            await writer.drain()
            writer.close()

    async def _handle_https(
            self,
            client_reader: StreamReader,
            client_writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handle https connection by making HTTP tunnel.
        """
        self._logger.debug(
            HANDLING_HTTPS_CONNECTION_MSG.format(url=r.host_url))
        server_reader, server_writer = await asyncio.open_connection(
            r.host_url, r.port
        )
        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self._logger.debug(CONNECTION_ESTABLISHED_MSG.format(url=r.abs_url))
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
            query = f"{r.method} {r.abs_url}"
        else:
            query = "Response from server"
        self._logger.debug(f"{sender_ip:<{len('255.255.255.255')}} "
                           f"{query} {data_size}")

    def _is_data_expired(
            self,
            resource_link: str
    ) -> bool:
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
        Save spent traffic to _spent_traffic_amount dict attribute.
        Used

        :param resource_link:
        :param chunk_size:
        :return:
        """
        for rsc in self._restricted:
            if any(re.search(pattern, resource_link) for
                   pattern in rsc.url_patterns) or \
                    rsc.host_url in resource_link:
                #  don't use rsh.host_url == r.host_url
                #  because r.host_url can contain extra www
                try:
                    self._spent_data_amount[rsc.host_url] += chunk_size
                except KeyError:
                    self._spent_data_amount[rsc.host_url] = chunk_size
                self._logger.info(f"{chunk_size} was spent for {rsc.host_url}")

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
                writer_ip = writer.get_extra_info("peername")[0]
                data = await reader.read(CHUNK_SIZE)
                is_data_expired = self._is_data_expired(r.host_url)
                is_writer_localhost = bool(writer_ip == "::1")
                if data and not is_data_expired:
                    self._log_forwarding(
                        writer_ip,
                        len(data),
                        r
                    )
                    writer.write(data)
                    await writer.drain()
                    #  save only incoming traffic
                    if is_writer_localhost:
                        self._save_traffic_amount(r.host_url, len(data))
                elif is_writer_localhost and is_data_expired and r.method != "CONNECT":
                    with open(DATA_LIMIT_PATH) as f:
                        writer.write(f"HTTP/1.1 200 OK\r\n\r\n{f.read()}".encode())
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    break
                else:
                    writer.close()
                    await writer.wait_closed()
                    break
            except ConnectionResetError:
                self._logger.info(CONNECTION_CLOSED_MSG.format(url=r.abs_url))
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
            self._forward(server_reader, client_writer, r),
            self._forward(client_reader, server_writer, r)
        )
