import pathlib
import re
from typing import Union


class RestrictedResource:

    def __init__(
            self,
            hostname: str,
            data_limit: int,
            response_page_path: Union[str, pathlib.Path]
    ):
        self.hostname = hostname
        self.data_limit = data_limit
        self.response_page_path = response_page_path
        self.spent_data = 0
        self.helpers = []
        if self.hostname == "vk.com":
            self.helpers = [
                re.compile(r".*\.vkuseraudio\.net"),
                re.compile(r"st\d{1,2}-\d{1,2}\.vk\.com"),
                re.compile(r"im\.vk\.com"),
                re.compile(r"sun\d-\d{1,2}\.userapi"),
                re.compile(r"queuev\d{1,2}\.vk\.com")
            ]
        elif self.hostname == "youtube.com":
            self.helpers = [
                re.compile(r".*yt.*\.com"),  # this just for luck catch
                re.compile(r"i\.ytimg\.com"),  # youtube images
                re.compile(r".*\.googlevideo\.com"),  # youtube videos
            ]

    def __str__(self):
        return f"{self.hostname}: {self.data_limit}"

    def http_content(self):
        with open(self.response_page_path) as f:
            return f.read()

    def is_data_lim_reached(self):
        return self.spent_data > self.data_limit

    def update_spent_data(self, chunk_size: int):
        self.spent_data += chunk_size
