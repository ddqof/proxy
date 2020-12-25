import re
from collections import namedtuple

method_regex = re.compile(r"^(\w+)")
url_regex = re.compile(r"\w+ (.+?) HTTP/\d.\d")
port_regex = re.compile(r":(\d+)$")


def parse(http_meta: bytes):
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
    r_method = extract_method(decoded_data)
    r_headers = build_headers(decoded_data)
    r_url = extract_url(decoded_data)
    r_port = extract_port(decoded_data)
    Request = namedtuple(
        "Request",
        ["method", "headers", "url", "raw", "port"]
    )
    if r_port is None:
        if r_method == "CONNECT":
            r_port = 443
        else:
            r_port = 80
    return Request(
        method=r_method,
        headers=r_headers,
        url=r_url,
        raw=http_meta,
        port=r_port
    )


def extract_method(http_meta: str) -> str:
    """
    Extracts and returns method from HTTP request body.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(method_regex, http_meta).group(1)


def extract_url(http_meta: str) -> str:
    """
    Extracts and returns url from HTTP request body.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(url_regex, http_meta, re.DOTALL).group(1)


def extract_port(http_url: str) -> str:
    """
    Extracts and returns port from HTTP request body.

    Params:
        http_meta: raw HTTP request body
    """
    return re.search(url_regex, http_url).group(1)


def build_headers(http_meta: str) -> dict:
    """
    Extracts and parses HTTP headers into dict-mapping
    from headers fields in theirs values.

    Params:
        http_meta: raw HTTP request body
    """
    #  removing first line with method
    h_lines = http_meta.split("\r\n")[1:]
    headers = {}
    for i in range(len(h_lines)):
        if h_lines[i]:
            field = h_lines[i].split(":")[0]
            value = h_lines[i].split(":")[1].strip()
            headers[field] = value
    return headers
