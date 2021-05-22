from pathlib import Path

LOCALHOST = "localhost"
START_SERVER_MSG = "Serving on {app_address}"
CONNECTION_ESTABLISHED_MSG = "Connection established: {url}"
CONNECTION_CLOSED_MSG = "Connection closed: {url}"
CONNECTION_REFUSED_MSG = "Connection refused: {method} {url}"
HANDLING_HTTP_REQUEST_MSG = "Handling HTTP request: {method} {url}"
HANDLING_HTTPS_CONNECTION_MSG = "Handling HTTPS connection: {url}"
BLACK_HOLE_MSG = "Black Hole: {url}"
BLOCKED_WEBPAGE = "Blocked: {url}"
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
