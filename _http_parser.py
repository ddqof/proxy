import re

method_regex = re.compile(r"^(\w+)")
url_regex = re.compile(r"\w+ (.+?) HTTP/\d.\d", re.DOTALL)
host_regex = re.compile(r"(^https?://|)([A-z.\-0-9]+)")
port_regex = re.compile(r":(\d+)$")


class Request:

    def __init__(self, method, url, host, raw, port):
        self.method = method
        self.url = url
        self.host = host
        self.raw = raw
        self.port = port


def parse(http_meta: bytes) -> Request:
    """
    Parse HTTP or HTTPS raw binary request body into.

    Params:
        http_meta: raw binary HTTP or HTTPS request body

    Returns:
        |namedtuple| Request("method", "headers", "url", "raw", "port").
         "method": HTTP request method.
         "headers": dict-mapping from HTTP request headers fields to
          theirs value.
         "url": absolute url requested in HTTP request. May also
          include port at the end of url.
         "raw": raw binary request body.
         "port": HTTP request port
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
        url=r_url,
        host=r_host,
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
    return re.search(host_regex, url).group(2)
