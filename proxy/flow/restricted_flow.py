import re
from typing import List

from proxy._restricted_resource import RestrictedResource
from proxy.connection.connection import Connection
from proxy.connection.greeting import HTTPScheme, Greeting
from proxy.flow.flow import Flow


class RestrictedFlow(Flow):

    def __init__(
            self,
            greeting: Greeting,
            client_conn: Connection,
            server_conn: Connection,
            chunk_size: int,
            restrictions: List[RestrictedResource]
    ):
        super().__init__(greeting, client_conn, server_conn, chunk_size)
        self.restriction = None
        for rsc in restrictions:
            if rsc.hostname == self._greeting.hostname:
                self.restriction = rsc
            for pattern in rsc.helpers:
                if re.search(pattern, self._greeting.hostname) is not None:
                    self.restriction = rsc

    async def send_reset_msg(self):
        if self.scheme is HTTPScheme.HTTPS:
            await self._client_conn.write(b"HTTP/1.1 403\r\n\r\n")
        else:
            await self._client_conn.write(self.restriction.http_content().encode())
        await self._client_conn.close()

    async def make(self):
        if self.restriction is None:
            await super().make()
        elif not self.restriction.is_data_lim_reached():
            recv_from_server = await super().make()
            self.restriction.update_spent_data(recv_from_server)
            return self.restriction
        else:
            await self.send_reset_msg()
