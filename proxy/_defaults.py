from pathlib import Path

LOCALHOST = "localhost"
CHUNK_SIZE = 2 ** 20
START_SERVER_MSG = "Serving on {app_address}"
CONNECTION_ESTABLISHED_MSG = "Connection established: {url}"
CONNECTION_CLOSED_MSG = "Connection closed: {url}"
CONNECTION_REFUSED_MSG = "Connection refused: {method} {url}"
HANDLING_HTTP_REQUEST_MSG = "Handling HTTP request: {method} {url}"
HANDLING_HTTPS_CONNECTION_MSG = "Handling HTTPS connection: {url}"
BLACK_HOLE_PATH = Path(__file__).parent / "service" / "black_hole_page.html"
DATA_LIMIT_PATH = Path(__file__).parent / "service" / "data_limit_page.html"
