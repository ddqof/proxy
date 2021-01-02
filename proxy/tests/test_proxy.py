import asyncio
import pytest
from asyncio import StreamReader, StreamWriter
from typing import Callable
from proxy._defaults import LOCALHOST
from proxy._http_parser import Request
from proxy.proxy import ProxyServer
from unittest.mock import patch


@pytest.fixture()
def proxy_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()


@pytest.fixture()
def server_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()


async def setup_proxy(port: int):
    proxy = ProxyServer(port)
    await proxy.run()


async def setup_server(port: int):
    server = await asyncio.start_server(handle, LOCALHOST, port)
    async with server:
        await server.serve_forever()


async def handle(reader: StreamReader, writer: StreamWriter):
    data = await reader.read(1024)
    if data.startswith(b"GET /"):
        writer.write(b"response for HTTP request")
        await writer.drain()
    writer.close()
    await writer.wait_closed()


async def send_then_recv(proxy_port: int, proxy_task: asyncio.Task, server_task: asyncio.Task):
    await asyncio.sleep(0.01)  # time to complete setting up servers
    cl_reader, cl_writer = await asyncio.open_connection(LOCALHOST, proxy_port)
    cl_writer.write(b"some message")
    try:
        return await cl_reader.read(1024)
    finally:
        proxy_task.cancel()
        server_task.cancel()


async def run_test(proxy_port: int, server_port: int, test_case: Callable):
    setup_proxy_task = asyncio.create_task(setup_proxy(proxy_port))
    setup_remote_server_task = asyncio.create_task(setup_server(server_port))
    testcase_task = asyncio.create_task(test_case(proxy_port, setup_proxy_task, setup_remote_server_task))
    try:
        await setup_proxy_task
        await setup_remote_server_task
        await testcase_task
    except asyncio.CancelledError:
        return testcase_task.result()


@pytest.mark.asyncio
@patch("proxy.proxy.parse")
async def test_http_single_request(parser_mock, proxy_port, server_port):
    parser_mock.return_value = Request(
        method="GET",
        abs_url=f"localhost:{server_port}",
        host_url="localhost",
        raw=f"GET / localhost:{server_port} HTTP/1.1\r\n\r\n".encode(),
        port=server_port
    )

    result = await run_test(proxy_port, server_port, send_then_recv)
    assert result == b"response for HTTP request"


@pytest.mark.asyncio
@patch("proxy.proxy.parse")
async def test_https_single_request(parser_mock, proxy_port, server_port):
    parser_mock.return_value = Request(
        method="CONNECT",
        abs_url=f"localhost:{server_port}",
        host_url="localhost",
        raw=f"CONNECT localhost:{server_port} HTTP/1.1\r\n\r\n".encode(),
        port=server_port
    )

    result = await run_test(proxy_port, server_port, send_then_recv)
    assert result == b"HTTP/1.1 200 Connection established\r\n\r\n"
