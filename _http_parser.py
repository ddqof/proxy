import re


class Request:

    def __init__(self, method: str, headers: dict, url: str, raw: bytes):
        self.method = method
        self.headers = headers
        self.url = url
        self.raw = raw
        if method == "CONNECT":
            self.port = 443
        else:
            try:
                self.port = self.headers["Host"].split(":")[1]
            except IndexError:
                self.port = 80

    def __str__(self):
        return f"Request {self.method} {self.url}"


def parse(http_meta: bytes):
    decoded_data = http_meta.decode()
    return Request(
        extract_method(decoded_data),
        build_headers(decoded_data),
        extract_url(decoded_data),
        http_meta
    )


def extract_method(http_meta: str):
    return http_meta.split()[0]


def extract_url(http_meta: str):
    return re.search(
        r"\w+ (.+?) HTTP/\d.\d",
        http_meta,
        re.DOTALL
    ).group(1)


def build_headers(http_meta: str):
    #  removing first line with method
    h_lines = http_meta.split("\r\n")[1:]
    headers = {}
    for i in range(len(h_lines)):
        if h_lines[i]:
            field = h_lines[i].split(":")[0]
            value = h_lines[i].split(":")[1].strip()
            headers[field] = value
    return headers
