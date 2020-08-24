#!/usr/bin/env python3

import socket

DEBUG = True


class ProxyServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', 8080))
        self.socket.listen(1)

    def start(self):
        while True:
            browser, addr = self.socket.accept()

            print(f'got connection with browser: {browser}')

            browser_msg = browser.recv(4096)
            if browser_msg == b'':
                continue
            print(f'got message: {browser_msg} from browser')

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            request_parts = browser_msg.decode('utf-8').split()[1].split('/')
            print(request_parts)
            if len(request_parts) > 1:
                url = request_parts[2]
            else:
                url = request_parts[0]

            url = url.split(':')

            print(f'url for connect is {url}')

            if len(url) == 1:
                url = url[0]
                server_socket.connect((url, 80))
            else:
                port = int(url[1])
                print(url)
                server_socket.connect((url, port))
            server_socket.send(browser_msg)

            print(f'message to server was sent')

            server_socket.settimeout(0.5)
            result = server_socket.recv(4096)
            while result != b'':
                browser.send(result)
                try:
                    result = server_socket.recv(4096)
                    print(result)
                except socket.error:
                    break
            print('got message form webserver')

            browser.close()
            server_socket.close()


def main():
    proxy = ProxyServer()
    proxy.start()


if __name__ == '__main__':
    main()
