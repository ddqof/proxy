#!/usr/bin/env python3

import asyncio
from defaults import HOST, HTTP_PORT
from http_parser import parse, remove_hops

DATA_AMOUNT = 2 ** 16


class ProxyServer:

    def __init__(self):
        self.timer = None

    async def reset_connection(self, writer: asyncio.StreamWriter):
        writer.close()
        await writer.wait_closed()

    async def run(self):
        server = await asyncio.start_server(
            self.handle_client, HOST, HTTP_PORT)

        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

    async def handle_client(self, browser_reader, browser_writer):
        request = await browser_reader.read(DATA_AMOUNT)
        if not request:
            return
        request_obj = parse(request)
        if request_obj.method == "CONNECT":
            await self.handle_https(browser_writer, request_obj)
        else:
            await self.handle_http(browser_writer, request_obj)

    async def handle_http(self, browser_writer, req):
        server_reader, server_writer = await asyncio.open_connection(req.headers["Host"], req.port)
        server_writer.write(remove_hops(req.raw))
        await server_writer.drain()
        server_response = await server_reader.read(DATA_AMOUNT)
        browser_writer.write(server_response)
        await browser_writer.drain()

    async def handle_https(self, browser_writer, req):
        return


# TODO: timeout

async def main():
    proxy = ProxyServer()
    await proxy.run()


asyncio.run(main())
