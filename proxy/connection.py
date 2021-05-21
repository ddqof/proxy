from proxy._proxy_request import ProxyRequest
from proxy.endpoint import Endpoint


class Connection:

    def __init__(
            self,
            client_endpoint: Endpoint,
            server_endpoint: Endpoint,
            pr: ProxyRequest
    ):
        self.client = client_endpoint
        self.server = server_endpoint
        self.pr = pr
