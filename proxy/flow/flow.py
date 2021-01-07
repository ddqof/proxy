import asyncio

from proxy.connection.greeting import HTTPScheme, Greeting
from proxy.connection.connection import Connection


class Flow:

    def __init__(
            self,
            greeting: Greeting,
            client_conn: Connection,
            server_conn: Connection,
            chunk_size: int
    ):
        self._greeting = greeting
        self.scheme = self._greeting.scheme
        self._chunk_size = chunk_size
        self._client_conn = client_conn
        self._server_conn = server_conn

    async def establish(self):
        if self.scheme is HTTPScheme.HTTPS:
            await self._client_conn.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        else:
            await self._server_conn.write(self._greeting.raw)

    async def make(self):
        from_server_to_client_task = asyncio.create_task(
            self._forward(self._server_conn, self._client_conn)
        )
        from_client_to_server_task = asyncio.create_task(
            self._forward(self._client_conn, self._server_conn)
        )
        try:
            if self.scheme is HTTPScheme.HTTPS:
                await asyncio.gather(
                    from_client_to_server_task,
                    from_server_to_client_task
                )
            else:
                await asyncio.gather(
                    from_server_to_client_task,
                    from_client_to_server_task
                )
            return from_server_to_client_task.result()
        except ConnectionResetError as e:
            print(e)

    async def _forward(self, conn_to_read, conn_to_write):
        msg_len = 0
        while True:
            data = await conn_to_read.read(self._chunk_size)
            msg_len += len(data)
            if not data:
                await conn_to_write.close()
                return msg_len
            await conn_to_write.write(data)