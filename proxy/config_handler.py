import re
from typing import List
from ._http_parser import get_host_from_url
from proxy_config import PROXY_CONFIG


class RestrictedResource:
    """
    Class represents restricted webpage
    """

    def __init__(self, host_url: str, data_limit: int):
        if type(data_limit) != int:
            raise ValueError("Provide integer as data limit in config file")
        self.host_url: str = host_url
        #  convert to megabytes
        self.data_limit: int = data_limit * 1_000_000
        if self.host_url == "youtube.com":
            self.url_patterns: List[re.Pattern] = [
                re.compile(r".*yt.*\.com"),  # this just for luck catch
                re.compile(r"i\.ytimg\.com"),  # youtube images
                re.compile(r".*\.googlevideo\.com"),  # youtube videos
            ]
        elif self.host_url == "vk.com":
            self.url_patterns: List[re.Pattern] = [
                re.compile(r".*\.vkuseraudio\.net"),
                re.compile(r"st\d{1,2}-\d{1,2}\.vk\.com"),
                re.compile(r"im\.vk\.com"),
                re.compile(r"sun\d-\d{1,2}\.userapi"),
                re.compile(r"queuev\d{1,2}\.vk\.com")
            ]
        else:
            self.url_patterns = []

    def __str__(self):
        return f"{self.host_url}: {self.data_limit}"


def get_restricted_list():
    """
    Returns list of restricted resources from proxy config.
    """
    return [
        RestrictedResource(get_host_from_url(item[0]), item[1])
        for item in PROXY_CONFIG["restricted_resources"].items()
    ]


def get_black_list():
    """
    Returns list of blacklist resources from proxy config.
    """
    return [
        get_host_from_url(url)
        for url in PROXY_CONFIG["black_list"]
    ]
