import pytest

from proxy._proxy_request import ProxyRequest


@pytest.fixture
def default_http_meta():
    return (b"GET http://example.com/ HTTP/1.1\r\n"
            b"Host: example.com\r\n"
            b"User-Agent: python-requests/2.25.0\r\n"
            b"Accept-Encoding: gzip, deflate\r\n"
            b"Accept: */*\r\n"
            b"Connection: keep-alive\r\n\r\n")


@pytest.fixture()
def https_meta_without_headers():
    #  requests lib doesn't send any
    #  headers within https request
    return b"CONNECT google.com:443 HTTP/1.0\r\n\r\n"


@pytest.fixture()
def https_meta_from_browser():
    return (b"CONNECT www.google.com:443 HTTP/1.1\r\n"
            b"Host: www.google.com:443\r\n"
            b"Proxy-Connection: keep-alive\r\n\r\n")


def test_get_method_from_def_http_meta(default_http_meta):
    assert ProxyRequest(default_http_meta).method == "GET"


def test_get_method_from_requests_https_meta(https_meta_without_headers):
    assert ProxyRequest(https_meta_without_headers).method == "CONNECT"


def test_get_method_from_browser_https_meta(https_meta_from_browser):
    assert ProxyRequest(https_meta_from_browser).method == "CONNECT"


def test_get_url_from_def_http_meta(default_http_meta):
    assert ProxyRequest(default_http_meta).abs_url == "http://example.com/"


def test_get_url_from_requests_https_meta(https_meta_without_headers):
    assert ProxyRequest(https_meta_without_headers).abs_url == "google.com:443"


def test_get_url_from_browser_https_meta(https_meta_from_browser):
    assert ProxyRequest(https_meta_from_browser).abs_url ==\
           "www.google.com:443"


def test_get_port_from_url_with_port(https_meta_from_browser):
    assert ProxyRequest(https_meta_from_browser).port == 443


def test_get_port_from_url_without_port(default_http_meta):
    assert ProxyRequest(default_http_meta).port == 80


def test_get_host_from_simple_http_url(default_http_meta):
    assert ProxyRequest(default_http_meta).hostname == "example.com"


def test_get_host_from_url_doesnt_catch_port(https_meta_without_headers):
    assert ProxyRequest(https_meta_without_headers).hostname == "google.com"


def test_get_host_from_url_doesnt_catch_www(https_meta_from_browser):
    assert ProxyRequest(https_meta_from_browser).hostname == "google.com"
