from pathlib import Path

LOCALHOST = "localhost"
CHUNK_SIZE = 2 ** 20
START_SERVER_MSG = "Serving on {app_address}"
CONNECTION_ESTABLISHED_MSG = "Connection established: {url}"
CONNECTION_CLOSED_MSG = "Connection closed: {url}"
CONNECTION_REFUSED_MSG = "Connection refused: {method} {url}"
HANDLING_HTTP_REQUEST_MSG = "Handling HTTP request: {method} {url}"
HANDLING_HTTPS_CONNECTION_MSG = "Handling HTTPS connection: {url}"
WEBPAGE_IS_BLOCKED_MSG = "Blocked: {url}"
WEBPAGE_IS_LIMITED_MSG = "Limited: {url}"
BLOCKED_RESOURCE_FILE_PATH = (
        Path(__file__).parent /
        "service" /
        "black_hole_page.html"
)
LIMITED_RESOURCE_FILE_PATH = (
        Path(__file__).parent /
        "service" /
        "data_limit_page.html"
)
