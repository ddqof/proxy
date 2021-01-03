from asyncio import StreamWriter
from proxy._http_parser import Request


class BadResponder:

    def __init__(
            self,
            black_hole_path,
            limit_page_path
    ):
        self.black_hole_path = black_hole_path
        self.limit_page_path = limit_page_path

    async def send_black_list_response(
            self,
            writer: StreamWriter,
            r: Request
    ) -> None:
        """
        Handles connection for blocked webpage.
        In HTTP case it sends HTML notification banner.
        In HTTPS case it sends not 200 status code that
        raises client error.
        """
        if r.method == "CONNECT":
            message = "HTTP/1.1 403\r\n\r\n"
        else:
            with open(self.black_hole_path) as f:
                message = f"HTTP/1.1 200 OK\r\n\r\n{f.read()}"
        writer.write(message.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def send_limited_page_response(
            self,
            writer: StreamWriter,
            r: Request
    ):
        """
        Handles connection for restricted webpage.
        In HTTP case it sends HTML notification page.
        In HTTPS case it closes connection.
        """
        if r.method != "CONNECT":
            with open(self.limit_page_path) as f:
                writer.write(
                    f"HTTP/1.1 200 OK\r\n\r\n{f.read()}".encode()
                )
            await writer.drain()
        writer.close()
        await writer.wait_closed()
