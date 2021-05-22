from asyncio import StreamReader, StreamWriter


class Endpoint:

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader = reader
        self.writer = writer

    async def write_and_drain(self, msg: bytes) -> None:
        self.writer.write(msg)
        await self.writer.drain()

    async def read(self, n) -> bytes:
        return await self.reader.read(n)

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()
