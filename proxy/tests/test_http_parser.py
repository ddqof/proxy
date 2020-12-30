import pytest
from unittest.mock import patch

from proxy._http_parser import (parse,
                                get_method,
                                get_url,
                                get_host_from_url,
                                get_port_from_url)


@pytest.fixture
def default_http_meta():
    return ("GET http://example.com/ HTTP/1.1\r\n"
            "Host: example.com\r\n"
            "User-Agent: python-requests/2.25.0\r\n"
            "Accept-Encoding: gzip, deflate\r\n"
            "Accept: */*\r\n"
            "Connection: keep-alive\r\n\r\n")


@pytest.fixture()
def https_meta_without_headers():
    #  requests lib doesn't send any
    #  headers within https request
    return "CONNECT google.com:443 HTTP/1.0\r\n\r\n"


@pytest.fixture()
def https_meta_from_browser():
    return ("CONNECT www.google.com:443 HTTP/1.1\r\n"
            "Host: www.google.com:443\r\n"
            "Proxy-Connection: keep-alive\r\n\r\n")


def test_get_method_from_def_http_meta(default_http_meta):
    assert get_method(default_http_meta) == "GET"


def test_get_method_from_requests_https_meta(https_meta_without_headers):
    assert get_method(https_meta_without_headers) == "CONNECT"


def test_get_method_from_browser_https_meta(https_meta_from_browser):
    assert get_method(https_meta_from_browser) == "CONNECT"


def test_get_url_from_def_http_meta(default_http_meta):
    assert get_url(default_http_meta) == "http://example.com/"


def test_get_url_from_requests_https_meta(https_meta_without_headers):
    assert get_url(https_meta_without_headers) == "google.com:443"


def test_get_url_from_browser_https_meta(https_meta_from_browser):
    assert get_url(https_meta_from_browser) == "www.google.com:443"


@patch("proxy._http_parser.get_method")
@patch("proxy._http_parser.get_url")
@patch("proxy._http_parser.get_port_from_url")
@patch("proxy._http_parser.get_host_from_url")
def test_parse(
        get_host_from_url_mock,
        get_port_from_url_mock,
        get_url_mock,
        get_method_mock,
):
    http_binary_data = b"some_http_meta"

    #  all this values are randomized
    get_method_mock.return_value = "MOCK_METHOD"
    get_url_mock.return_value = "some_url"
    get_port_from_url_mock.return_value = "secret_port"
    get_host_from_url_mock.return_value = "some_host"

    r = parse(http_binary_data)

    decoded_data = http_binary_data.decode()
    get_method_mock.assert_called_once_with(decoded_data)
    get_url_mock.assert_called_once_with(decoded_data)
    get_port_from_url_mock.assert_called_once_with("some_url")
    get_host_from_url_mock.assert_called_once_with("some_url")

    assert r.abs_url == "some_url"
    assert r.method == "MOCK_METHOD"
    assert r.port == "secret_port"
    assert r.raw == http_binary_data
    assert r.host_url == "some_host"


def test_get_port_from_url_with_port():
    assert get_port_from_url("www.google.com:443") == "443"


def test_get_port_from_url_without_port():
    assert get_port_from_url("http://example.com/") is None


def test_get_host_from_simple_http_url():
    assert get_host_from_url("http://example.com") == "example.com"


def test_get_host_from_http_url_with_path():
    assert get_host_from_url(
        "http://example.com/some/secret_file.txt"
    ) == "example.com"


def test_get_host_from_simple_https_url():
    assert get_host_from_url("https://example.com") == "example.com"


def test_get_host_from_https_url_with_path():
    assert get_host_from_url(
        "https://example.com/some/secret_file.txt"
    ) == "example.com"


def test_get_host_from_url_doesnt_catch_port():
    assert get_host_from_url("google.com:443") == "google.com"


def test_get_host_from_url_catch_www():
    assert get_host_from_url("www.google.com") == "www.google.com"
