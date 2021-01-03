from proxy._restricted_resource import RestrictedResource
from proxy._http_parser import get_host_from_url
from config import PROXY_CONFIG


def restricted_list_from_cfg():
    """
    Returns list of restricted resources from proxy config.
    """
    return [
        RestrictedResource(get_host_from_url(item[0]), item[1])
        for item in PROXY_CONFIG["restricted_resources"].items()
    ]


def black_list_from_cfg():
    """
    Returns list of blacklist resources from proxy config.
    """
    return [
        get_host_from_url(url)
        for url in PROXY_CONFIG["black_list"]
    ]
