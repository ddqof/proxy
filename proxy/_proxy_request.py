import re
from collections import namedtuple
from enum import Enum, auto
from pathlib import Path

from proxy._defaults import (LIMITED_RESOURCE_FILE_PATH,
                             BLOCKED_RESOURCE_FILE_PATH)


class HTTPScheme(Enum):
    HTTP = auto()
    HTTPS = auto()


class ProxyRequest:
    """
     "raw": raw binary request body.
     "method": HTTP request method.
     "abs_url": absolute url requested in HTTP request. May also
      include port at the end.
     "port": port specified in HTTP request
     "hostname": url of host
     "scheme": scheme of HTTP connection
    """

    def __init__(self, raw_data: bytes, config=None):
        self.raw = raw_data
        self._decoded_meta = self.raw.decode()
        self._method_regex = re.compile(r"^(\w+)")
        self._url_regex = re.compile(r"\w+ (.+?) HTTP/\d.\d", re.DOTALL)
        self._host_regex = re.compile(r"(^https?://|)(www.)?([A-z.\-0-9]+)")
        self._port_regex = re.compile(r":(\d+)$")
        self.method = re.search(
            self._method_regex, self._decoded_meta
        ).group(1)
        if self.method == "CONNECT":
            self.scheme = HTTPScheme.HTTPS
        else:
            self.scheme = HTTPScheme.HTTP
        self.abs_url = re.search(self._url_regex, self._decoded_meta).group(1)
        self.hostname = re.search(self._host_regex, self.abs_url).group(3)
        port_mo = re.search(self._port_regex, self.abs_url)
        if port_mo is not None:
            self.port = int(port_mo.group(1))
        else:
            if self.scheme is HTTPScheme.HTTPS:
                self.port = 443
            else:
                self.port = 80
        if config is None:
            self.restriction = None
        else:
            self.restriction = self._check_restrictions(config)

    def _check_restrictions(self, config):
        vk_helpers = [
            re.compile(r".*\.vkuseraudio\.net"),
            re.compile(r"st\d{1,2}-\d{1,2}\.vk\.com"),
            re.compile(r"im\.vk\.com"),
            re.compile(r"sun\d-\d{1,2}\.userapi"),
            re.compile(r"queuev\d{1,2}\.vk\.com"),
            re.compile(r"vk\.com")
        ]
        yt_helpers = [
            re.compile(r".*yt.*\.com"),  # this just for luck catch
            re.compile(r"i\.ytimg\.com"),  # youtube images
            re.compile(r".*\.googlevideo\.com"),  # youtube videos
            re.compile(r"youtube\.com")
        ]
        RestrictedResource = namedtuple(
            "RestrictedResource", ["initiator", "data_limit", "http_content"]
        )
        initiator = self.hostname
        if any(re.search(pattern, self.hostname) for pattern in vk_helpers):
            initiator = "vk.com"
        elif any(re.search(pattern, self.hostname) for pattern in yt_helpers):
            initiator = "youtube.com"
        for hostname in config["black-list"]:
            if hostname == initiator:
                return RestrictedResource(
                    initiator,
                    0,
                    Path(BLOCKED_RESOURCE_FILE_PATH).read_text()
                )
        for hostname in config["limited"]:
            if hostname == initiator:
                return RestrictedResource(
                    initiator,
                    config["limited"][hostname],
                    Path(LIMITED_RESOURCE_FILE_PATH).read_text()
                )
