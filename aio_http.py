import asyncio
import aiohttp
from aiohttp import web
from defaults import HTTP_PORT, HTTPS_PORT, HOST


async def http_handler(request):
    if request.method == "CONNECT":
        await http_handler(request)
    async with aiohttp.ClientSession() as client:
        async with client.request(request.method, request.url) as resp:
            response = web.StreamResponse(
                status=resp.status,
                headers=resp.headers
            )
            await response.prepare(request)
            await response.write(await resp.content.read())


async def https_handler(request):
    if request.method == "CONNECT":
        async with aiohttp.ClientSession() as session:
            async with session.request(
                    request.method,
                    request.url,
                    proxy="http://127.0.0.1:8080"
            ) as resp:
                print(resp.status)


async def setup_http():
    server = web.Server(http_handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, HOST, HTTP_PORT)
    await site.start()


async def setup_https():
    server = web.Server(https_handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, HOST, HTTPS_PORT)
    await site.start()


async def main():
    await setup_http()
    await setup_https()

    print("======= Serving on http://127.0.0.1:8080/ ======")


loop = asyncio.get_event_loop()

try:
    loop.create_task(main())
    loop.run_forever()
except KeyboardInterrupt:
    pass
loop.close()
