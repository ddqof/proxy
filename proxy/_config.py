from proxy._defaults import (LIMITED_RESOURCE_FILE_PATH,
                             BLOCKED_RESOURCE_FILE_PATH)
from proxy._restricted_resource import RestrictedResource


class ProxyConfig:

    def __init__(self, data: dict):
        self.data = data

    def restrictions(self):
        result = [
            RestrictedResource(item[0], item[1], LIMITED_RESOURCE_FILE_PATH)
            for item in self.data["limited"].items()
        ]
        for hostname in self.data["black_list"]:
            result.append(
                RestrictedResource(hostname, 0, BLOCKED_RESOURCE_FILE_PATH)
            )
        return result
