import re
from enum import Enum, auto

method_regex = re.compile(r"^(\w+)")
url_regex = re.compile(r"\w+ (.+?) HTTP/\d.\d", re.DOTALL)
host_regex = re.compile(r"(^https?://|)(www.)?([A-z.\-0-9]+)")
port_regex = re.compile(r":(\d+)$")


class HTTPScheme(Enum):
    HTTP = auto()
    HTTPS = auto()


class Greeting:

    def __init__(self, data: bytes):  # TODO: доделать этот класс
        """
         "method": HTTP request method.
         "abs_url": absolute url requested in HTTP request. May also
          include port at the end.
         "host_url": url of host
         "raw": raw binary request body.
         "port": port specified in HTTP request
        """
        decoded_data = data.decode()
        self.method = Greeting.get_method(decoded_data)
        if self.method == "CONNECT":
            self.scheme = HTTPScheme.HTTPS
        else:
            self.scheme = HTTPScheme.HTTP
        self.abs_url = Greeting.get_url(decoded_data)
        self.port = Greeting.get_port_from_url(self.abs_url)
        if self.port is None:
            if self.scheme is HTTPScheme.HTTPS:
                self.port = 443
            else:
                self.port = 80
        self.hostname = Greeting.get_host_from_url(self.abs_url)
        self.raw = data

    def __str__(self):
        return f"{self.method} {self.abs_url}"

    @staticmethod
    def get_method(http_meta: str) -> str:
        """
        Returns method from HTTP request body.

        Params:
            http_meta: raw HTTP request body
        """
        return re.search(method_regex, http_meta).group(1)

    @staticmethod
    def get_url(http_meta: str) -> str:
        """
        Returns absolute url from HTTP request body.

        Params:
            http_meta: raw HTTP request body
        """
        return re.search(url_regex, http_meta).group(1)

    @staticmethod
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

    @staticmethod
    def get_host_from_url(url: str) -> str:
        """
        Returns hostname from url.

        Params:
            http_meta: raw HTTP request body
        """
        return re.search(host_regex, url).group(3)
