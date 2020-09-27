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
        self.request_data = None

    def get_url_with_port(self):
        url, port = None, None
        if len(self.request_data.netloc.split(':')) == 2:  # properly wrote url with http/https scheme
            url = self.request_data.netloc.split(':')[0]
            port = self.request_data.netloc.split(':')[1]
        elif self.request_data.scheme == '' and \
                len(self.request_data.path.split(':')) == 2:  # url without http/https scheme
            url = self.request_data.path.split(':')[0]
            port = int(self.request_data.path.split(':')[1])
        elif self.request_data.scheme == 'http':
            url = self.request_data.netloc
            port = 80

        return url, port

    def run(self):
        while True:
            browser_socket, addr = self.socket.accept()

            request = browser_socket.recv(DATA_AMOUNT)
            method = request.decode('latin-1').split()[0]
            print(request.decode('latin-1'))
            self.request_data = urlparse(request.decode('latin-1').split()[1])
            url, port = self.get_url_with_port()
            print(str(addr), method, url + '\n')
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            with server_socket, browser_socket:
                try:  # weird urls
                    if method == 'CONNECT':
                        print((url, port))
                        server_socket.connect((url, port))
                        browser_socket.send(b'HTTP/1.0 200 Connection established\r\nProxy-agent: Pyx\r\n\r\n')
                    else:
                        server_socket.connect((url, port))
                except socket.gaierror:
                    print(f'Connection refused: {self.request_data.netloc}\n')
                    continue
                browser_socket.setblocking(False)
                server_socket.setblocking(False)
                while True:
                    try:
                        request = browser_socket.recv(DATA_AMOUNT)
                        server_socket.send(request)
                    except socket.error:
                        pass
                    try:
                        reply = server_socket.recv(DATA_AMOUNT)
                        browser_socket.send(reply)
                    except socket.error:
                        pass


def main():
    proxy = ProxyServer()
    for _ in range(10):
        thread = threading.Thread(target=proxy.run)
        thread.start()


if __name__ == '__main__':
    main()
