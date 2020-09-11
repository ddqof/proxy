#!/usr/bin/env python3

import socket
import threading
from urllib.parse import urlparse

DATA_AMOUNT = 2 ** 20


class ProxyServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('localhost', 8080))
        self.socket.listen()

    def run(self):
        while True:
            client_socket, addr = self.socket.accept()

            request = client_socket.recv(DATA_AMOUNT)

            url = request.decode('latin-1').split()[1]
            if 'http' not in url:
                url = 'http://' + url
            request_data = urlparse(url)

            print(str(addr) + '\t' + request.decode('latin-1').split()[0] + '\t' + url)
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            with server_socket, client_socket:
                try:  # weird urls
                    if request_data.port is None:
                        server_socket.connect((request_data.netloc, 80))
                    else:
                        url = request_data.netloc.split(':')[0]
                        port = int(request_data.netloc.split(':')[1])
                        server_socket.connect((url, port))
                except socket.error:
                    print(f'Connection refused: {request_data.netloc}')
                    continue
                server_socket.send(request)

                try:
                    result = server_socket.recv(DATA_AMOUNT)
                    while result:
                        client_socket.send(result)
                        result = server_socket.recv(DATA_AMOUNT)
                except ConnectionResetError:
                    continue


def main():
    proxy = ProxyServer()
    for _ in range(10):
        thread = threading.Thread(target=proxy.run)
        thread.start()


if __name__ == '__main__':
    main()
