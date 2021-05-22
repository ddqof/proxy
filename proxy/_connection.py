import logging

from proxy._defaults import BLACK_HOLE_MSG, BLOCKED_WEBPAGE
from proxy._endpoint import Endpoint
from proxy._proxy_request import ProxyRequest, HTTPScheme
from proxy.enpoint_type import EndpointType

CHUNK_SIZE = 2 ** 20
IMG_EXTS = {".jpg", ".jpeg", ".png"}
HTTP_RESET_MSG = b"HTTP/1.1 403\r\n\r\n"

LOGGER = logging.getLogger("proxy.proxy")


class Connection:

    def __init__(
            self,
            client_endpoint: Endpoint,
            server_endpoint: Endpoint,
            pr: ProxyRequest,
            block_images: bool
    ):
        self.client = client_endpoint
        self.server = server_endpoint
        self.pr = pr
        self.block_images = block_images

    async def forward_to_server(self) -> None:
        while True:
            data = await self.client.read(CHUNK_SIZE)
            if not data:
                await self.server.close()
                break
            elif self.block_images:
                try:
                    decoded_data = data.decode()
                    if (x in decoded_data for x in IMG_EXTS):
                        await self.client.write_and_drain(HTTP_RESET_MSG)
                        await self.client.close()
                        return
                except UnicodeDecodeError:
                    pass
            await self.server.write_and_drain(data)
            self._log_forwarding(EndpointType.SERVER, data)

    async def forward_to_client(self, spent: dict) -> None:
        """
        Receives data from remote server and forward it to localhost.
        """
        while True:
            data = await self.server.read(CHUNK_SIZE)
            restriction = self.pr.restriction
            if data:
                if restriction:
                    initiator = restriction.initiator
                    if spent[initiator] >= restriction.data_limit:
                        await self._handle_limited_page()
                        break
                    spent[initiator] += len(data)
                    LOGGER.debug(f"{spent[initiator]} SPENT FOR {initiator}")
                await self.client.write_and_drain(data)
                self._log_forwarding(EndpointType.CLIENT, data)
            else:
                await self.client.close()
                break

    async def _handle_limited_page(self) -> None:
        """
        Handles connection for restricted webpage.
        In HTTP case it sends HTML notification page.
        In HTTPS case it closes connection.
        """
        rsc = self.pr.restriction
        if rsc.data_limit == 0:
            LOGGER.info(BLACK_HOLE_MSG.format(url=rsc.initiator))
        else:
            LOGGER.info(BLOCKED_WEBPAGE.format(url=rsc.initiator))
        if self.pr.scheme is HTTPScheme.HTTPS:
            msg = "HTTP/1.1 403\r\n\r\n"
        else:
            msg = f"HTTP/1.1 200 OK\r\n\r\n{rsc.http_content}"
        await self.client.write_and_drain(msg.encode())
        await self.client.close()

    async def reset(self):
        LOGGER.info(f"Blocked image {self.pr.method:<{len('CONNECT')}} "
                    f"{self.pr.abs_url}")
        await self.client.write_and_drain(HTTP_RESET_MSG)
        await self.client.close()

    def _log_forwarding(self, endpoint_type: EndpointType, data: bytes):
        """
        Logging forwarding message.
        """
        query = f"{self.pr.method} {self.pr.abs_url}"
        if endpoint_type is EndpointType.SERVER:
            sender_ip = self.server.writer.get_extra_info("peername")[0]
        else:
            sender_ip = self.client.writer.get_extra_info("peername")[0]
        if sender_ip == "::1":
            pass
        else:
            query = "Response from server"
        LOGGER.debug(f"{sender_ip:<{len('255.255.255.255')}} "
                     f"{query} {len(data)}")
