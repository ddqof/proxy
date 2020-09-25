import asyncio
import aiohttp
from aiohttp import web


async def handler(request):  # TODO: implement https, how to throw errors in browser
    async with aiohttp.ClientSession() as session:
        print(request.method, request.url)
        async with session.request(request.method, request.url) as resp:
            print(resp.url, resp.status)
            return web.Response(body=await resp.read(), content_type=resp.content_type,
                                charset=resp.charset, status=resp.status, reason=resp.reason)


async def server_handle():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    print("======= Serving on http://127.0.0.1:8080/ ======")

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption
    await asyncio.sleep(100 * 3600)


def main():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(server_handle())
    except KeyboardInterrupt:
        pass
    loop.close()


if __name__ == '__main__':
    main()
