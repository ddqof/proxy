
class ProxyServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((HOST, HTTP_PORT))
        self.socket.listen()

    def handle_http1(self):
        # while True:
        #     browser_socket, addr = self.socket.accept()
        #     raw_request = browser_socket.recv(DATA_AMOUNT)
        #     request_obj = parse(raw_request)
        #     if request_obj.method == "CONNECT":
        #         continue
        #     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #     try:  # weird urlsasync
        #         server_socket.connect(
        #             (request_obj.headers["Host"], request_obj.port)
        #         )
        #     except socket.gaierror:
        #         print(f"Connection refused: {request_obj.url}\n")
        #         continue
        #     with server_socket, browser_socket:
        #         try:
        #             new_req = change_path(raw_request, request_obj.url, request_obj.path)
        #             server_socket.send(new_req)
        #         except socket.error:
        #             continue
        #         while True:
        #             try:
        #                 reply = server_socket.recv(DATA_AMOUNT)
        #                 print(len(reply))
        #                 if not reply:
        #                     browser_socket.close()
        #                     break
        #                 browser_socket.send(reply)
        #             except socket.error:
        #                 continue
        pass
