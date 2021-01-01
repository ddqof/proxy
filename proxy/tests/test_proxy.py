import asyncio
import pytest
from proxy._defaults import LOCALHOST
from proxy._http_parser import Request
from unittest.mock import patch
from asyncio import StreamReader, StreamWriter
from proxy.proxy import ProxyServer


@pytest.fixture()
def proxy_port():
    return 9999


@pytest.fixture()
def server_port():
    return 10000


async def setup_proxy(port):
    proxy = ProxyServer(port)
    await proxy.run()


async def setup_server(port):
    server = await asyncio.start_server(handle, LOCALHOST, port)
    async with server:
        await server.serve_forever()


async def handle(reader: StreamReader, writer: StreamWriter):
    data = await reader.read(1024)
    if data.startswith(b"TEST_METHOD"):
        writer.write(b"hello from server")
        await writer.drain()
    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test(proxy_port, server_port):
    async def case(proxy_task: asyncio.Task, server_task: asyncio.Task):
        cl_reader, cl_writer = await asyncio.open_connection(LOCALHOST, proxy_port)
        cl_writer.write(f"TEST_METHOD localhost:{server_port}"
                        f" HTTP/1.0\r\n\r\n".encode())
        try:
            return await cl_reader.read(1024)
        finally:
            proxy_task.cancel()
            server_task.cancel()

    setup_proxy_task = asyncio.create_task(setup_proxy(proxy_port))
    setup_remote_server_task = asyncio.create_task(setup_server(server_port))
    testcase_task = asyncio.create_task(case(setup_proxy_task, setup_remote_server_task))
    try:
        await setup_proxy_task
        await asyncio.sleep(1)
        await setup_remote_server_task
        await testcase_task
    except asyncio.CancelledError:
        pass
    assert testcase_task.result() == b"hello from server"
