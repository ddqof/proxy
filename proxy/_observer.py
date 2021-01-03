import re
from typing import List
from proxy._restricted_resource import RestrictedResource


class Observer:

    def __init__(
            self,
            restricted: List[RestrictedResource] = None,
            black_list: List[str] = None,
    ):
        if restricted is None:
            restricted = []
        if black_list is None:
            black_list = []

        self._restricted = restricted
        self._black_list = black_list
        self._spent_data = {}

    def is_link_in_black_list(
            self,
            request_link: str
    ) -> bool:
        return any(link in request_link for link in self._black_list)

    def is_data_lim_reached(
            self,
            resource_link: str
    ) -> bool:
        """
        Check if data limit is reached for particular resource.
        Used for control traffic from restricted resources.
        """
        for rsc in self._restricted:
            if any(re.search(pattern, resource_link) for
                   pattern in rsc.url_patterns) or \
                    rsc.host_url == resource_link:
                try:
                    return self._spent_data[rsc.host_url] > \
                           rsc.data_limit
                except KeyError:
                    return False

    def update_state(
            self,
            resource_link: str,
            chunk_size: int
    ) -> str:
        """
        Save spent traffic amount for providing control of
        restricted resources.

        Returns:
            Message that N bytes was spent for "resource_link" webpage
        """
        for rsc in self._restricted:
            if any(re.search(pattern, resource_link) for
                   pattern in rsc.url_patterns) or \
                    rsc.host_url == resource_link:
                try:
                    self._spent_data[rsc.host_url] += chunk_size
                except KeyError:
                    self._spent_data[rsc.host_url] = chunk_size
                finally:
                    return (f"{self._spent_data[rsc.host_url]}"
                            f" WAS SPENT FOR {rsc.host_url}")
