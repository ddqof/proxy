#!/usr/bin/env python3

import asyncio
import sys
from proxy.proxy import ProxyServer
from _arg_parser import parse_args
from cfg import PROXY_CONFIG

if __name__ == '__main__':
    args = parse_args()
    proxy = ProxyServer(args.port, PROXY_CONFIG)
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        sys.exit(1)
