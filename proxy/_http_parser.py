import re
from typing import NamedTuple

method_regex = re.compile(r"^(\w+)")
url_regex = re.compile(r"\w+ (.+?) HTTP/\d.\d", re.DOTALL)
host_regex = re.compile(r"(^https?://|)(www.)?([A-z.\-0-9]+)")
port_regex = re.compile(r":(\d+)$")


class Request(NamedTuple):
    """
     "method": HTTP request method.
     "abs_url": absolute url requested in HTTP request. May also
      include port at the end.
     "host_url": url of host
     "raw": raw binary request body.
     "port": port specified in HTTP request
    """
    method: str
    abs_url: str
    host_url: str
    raw: bytes
    port: int


def parse(http_meta: bytes) -> Request:
    """
    Parse HTTP(S) raw binary request body into.

    Params:
        http_meta: raw binary HTTP(S) request body

    Returns:
        |Request| object
        |namedtuple| Request("method", "headers", "url", "raw", "port").

    """
    decoded_data = http_meta.decode()
    r_method = get_method(decoded_data)
    r_url = get_url(decoded_data)
    r_port = get_port_from_url(r_url)
    if r_port is None:
        if r_method == "CONNECT":
            r_port = 443
        else:
            r_port = 80
    r_host = get_host_from_url(r_url)
    return Request(
        method=r_method,
        abs_url=r_url,
        host_url=r_host,
        raw=http_meta,
        port=r_port
    )


def get_method(http_meta: str) -> str:
    """
    Returns method from HTTP request body.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(method_regex, http_meta).group(1)


def get_url(http_meta: str) -> str:
    """
    Returns absolute url from HTTP request body.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(url_regex, http_meta).group(1)


def get_port_from_url(url: str) -> str:
    """
    Returns port from url.

    Params:
        http_meta: raw HTTP request body
    """
    mo = re.search(port_regex, url)
    if mo is not None:
        res = mo.group(1)
    else:
        res = None
    return res


def get_host_from_url(url: str) -> str:
    """
    Returns hostname from url.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(host_regex, url).group(3)
