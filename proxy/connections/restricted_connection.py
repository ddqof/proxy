import re

from asyncio import StreamReader, StreamWriter
from typing import List
from proxy._restricted_resource import RestrictedResource
from proxy.connections.connection import Connection
from proxy.connections.greeting import Greeting


class RestrictedConnection(Connection):

    def __init__(
            self,
            greeting: Greeting,
            reader: StreamReader,
            writer: StreamWriter,
            restricted: List[RestrictedResource],
    ):
        super().__init__(greeting.scheme, reader, writer)
        self.scheme = greeting.scheme
        self.restricted = None
        for rsc in restricted:
            if rsc.hostname == greeting.hostname:
                self.restricted = rsc
            for pattern in rsc.helpers:
                if re.search(pattern, greeting.hostname) is not None:
                    self.restricted = rsc
        self._reader = reader
        self._writer = writer

    def is_expired(self):
        if self.restricted is None:
            return False
        return self.restricted.is_data_lim_reached()

    def update_rsc_balance(self, wasted: int):
        self.restricted.update_spent_data(wasted)

    def send_reset_msg(self):
        self.write(self.restricted.http_content())
