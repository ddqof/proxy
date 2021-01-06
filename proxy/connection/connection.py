from asyncio import StreamReader, StreamWriter


class Connection:

    def __init__(
            self,
            reader: StreamReader,
            writer: StreamWriter,
    ):
        self._reader = reader
        self._writer = writer

    async def read(self, data_size) -> bytes:
        data = await self._reader.read(data_size)
        return data

    async def write(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()
