#!/usr/bin/env python3

import socket

DEBUG = True


class ProxyServer:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', 8080))
        self.socket.listen(10)

    def start(self):
        while True:
            browser, addr = self.socket.accept()

            print(f'got connection with browser: {browser}')

            browser_msg = browser.recv(4096)
            if browser_msg == b'':
                continue

            print(f'got message from browser: {browser_msg}')

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            full_url = browser_msg.decode('utf-8').split()[1][7:-1]

            print(f'full url is {full_url}')

            url = full_url.split('/')[0].split(':')

            print(f'url for connect is {url[0]}')

            if len(url) == 1:
                server_socket.connect((url[0], 80))
            else:
                server_socket.connect((url[0], int(url[1])))
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
