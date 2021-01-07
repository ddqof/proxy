import pathlib
from typing import Union


class RestrictedResource:

    def __init__(
            self,
            hostname: str,
            data_limit: int,
            response_page_path: Union[str, pathlib.Path],
    ):
        self.hostname = hostname
        self.data_limit = data_limit
        self.spent_data = 0
        self._response_page_path = response_page_path

    def __str__(self):
        return f"{self.hostname}: {self.data_limit}"

    def http_content(self):
        with open(self._response_page_path) as f:
            return f.read()
