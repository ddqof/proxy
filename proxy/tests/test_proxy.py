import asyncio
from asyncio import StreamReader, StreamWriter
from typing import Callable
from unittest.mock import patch

import pytest

from proxy._defaults import (BLOCKED_RESOURCE_FILE_PATH,
                             LIMITED_RESOURCE_FILE_PATH)
from proxy._defaults import LOCALHOST
from proxy._proxy_request import HTTPScheme, RestrictedResource
from proxy.proxy import ProxyServer

EMPTY_CFG = {"limited": {}, "black-list": []}


# SETUP TEST SERVERS

@pytest.fixture
def proxy_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()


@pytest.fixture
def server_port(unused_tcp_port_factory):
    return unused_tcp_port_factory()


async def setup_proxy(port: int, cfg: dict = None):
    proxy = ProxyServer(port, False, cfg)
    await proxy.run()


async def setup_server(port: int):
    server = await asyncio.start_server(handle, LOCALHOST, port)
    async with server:
        await server.serve_forever()


async def handle(
        reader: StreamReader,
        writer: StreamWriter
):
    data = await reader.read(1024)
    if data.startswith(b"GET /"):
        writer.write(b"response for HTTP request")
        await writer.drain()
    writer.close()
    await writer.wait_closed()


# TEST CASES

def fill_http_mock(mock, server_port, restriction=None):
    mock_value = mock.return_value
    mock_value.method = "GET"
    mock_value.abs_url = f"localhost:{server_port}"
    mock_value.hostname = "localhost"
    mock_value.raw = f"GET / localhost:{server_port} HTTP/1.1\r\n\r\n".encode()
    mock_value.port = server_port
    mock_value.scheme = HTTPScheme.HTTP
    mock_value.restriction = restriction


def fill_https_mock(mock, server_port, restriction=None):
    mock_value = mock.return_value
    mock_value.method = "CONNECT"
    mock_value.abs_url = f"localhost:{server_port}"
    mock_value.hostname = "localhost"
    mock_value.raw = f"CONNECT localhost:{server_port} " \
                     f"HTTP/1.1\r\n\r\n".encode()
    mock_value.port = server_port
    mock_value.scheme = HTTPScheme.HTTPS
    mock_value.restriction = restriction


@pytest.mark.asyncio
async def test_http_single_request(proxy_port, server_port):
    with patch("proxy.proxy.ProxyRequest") as PrMock:
        fill_http_mock(PrMock, server_port)
        result = await run_test(
            EMPTY_CFG, send_then_recv, proxy_port, server_port
        )
        assert result == b"response for HTTP request"


@pytest.mark.asyncio
async def test_https_single_request(proxy_port, server_port):
    with patch("proxy.proxy.ProxyRequest") as PrMock:
        fill_https_mock(PrMock, server_port)
        result = await run_test(
            EMPTY_CFG, send_then_recv, proxy_port, server_port
        )
        assert result == b"HTTP/1.1 200 Connection established\r\n\r\n"


@pytest.mark.asyncio
async def test_http_blacklist(proxy_port, server_port):
    with patch("proxy.proxy.ProxyRequest") as PrMock:
        restriction = RestrictedResource(
            "localhost", 0, BLOCKED_RESOURCE_FILE_PATH.read_text()
        )
        fill_http_mock(PrMock, server_port, restriction)
        cfg = {"limited": {}, "black-list": ["localhost"]}
        result = await run_test(cfg, send_then_recv, proxy_port, server_port)
        with open(BLOCKED_RESOURCE_FILE_PATH) as f:
            assert result == f"HTTP/1.1 200 OK\r\n\r\n{f.read()}".encode()


@pytest.mark.asyncio
async def test_https_blacklist(proxy_port, server_port):
    with patch("proxy.proxy.ProxyRequest") as PrMock:
        restriction = RestrictedResource(
            "localhost", 0, BLOCKED_RESOURCE_FILE_PATH.read_text()
        )
        fill_https_mock(PrMock, server_port, restriction)
        cfg = {"black-list": ["localhost"], "limited": {}}
        result = await run_test(cfg, send_then_recv, proxy_port, server_port)
        assert result == b"HTTP/1.1 403\r\n\r\n"


@pytest.mark.asyncio
async def test_http_restrict(proxy_port, server_port):
    with patch("proxy.proxy.ProxyRequest") as PrMock:
        restriction = RestrictedResource(
            "localhost",
            len(b"some message"),
            LIMITED_RESOURCE_FILE_PATH.read_text()
        )
        fill_http_mock(PrMock, server_port, restriction)
        cfg = {"limited": {LOCALHOST: len(b"some message")}, "black-list": []}
        result = await run_test(cfg, send_until_limit, proxy_port, server_port)
        with open(LIMITED_RESOURCE_FILE_PATH) as f:
            assert result == f"HTTP/1.1 200 OK\r\n\r\n{f.read()}".encode()


async def send_until_limit(
        proxy_port: int,
        proxy_task: asyncio.Task,
        server_task: asyncio.Task
):
    await asyncio.sleep(0.01)  # time to complete setting up servers
    first_reader, first_writer = await asyncio.open_connection(
        LOCALHOST, proxy_port
    )
    first_writer.write(b"some message")
    await first_writer.drain()
    second_reader, second_writer = await asyncio.open_connection(
        LOCALHOST, proxy_port
    )
    second_writer.write(b"this message will be blocked")
    await second_writer.drain()
    try:
        return await second_reader.read(4096)
    finally:
        proxy_task.cancel()
        server_task.cancel()


async def send_then_recv(
        proxy_port: int,
        proxy_task: asyncio.Task,
        server_task: asyncio.Task
):
    await asyncio.sleep(0.01)  # time to complete setting up servers
    cl_reader, cl_writer = await asyncio.open_connection(LOCALHOST, proxy_port)
    cl_writer.write(b"some message")
    try:
        return await cl_reader.read(4096)
    finally:
        proxy_task.cancel()
        server_task.cancel()


async def run_test(cfg: dict, test_case: Callable, proxy_port, server_port):
    setup_proxy_task = asyncio.create_task(setup_proxy(proxy_port, cfg))
    setup_remote_server_task = asyncio.create_task(setup_server(server_port))
    testcase_task = asyncio.create_task(
        test_case(proxy_port, setup_proxy_task, setup_remote_server_task)
    )
    try:
        await setup_proxy_task
        await setup_remote_server_task
        await testcase_task
    except asyncio.CancelledError:
        return testcase_task.result()
