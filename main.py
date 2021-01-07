#!/usr/bin/env python3

import asyncio
import sys
from cfg import PROXY_CONFIG
from proxy.proxy import ProxyServer
from _arg_parser import parse_args

if __name__ == '__main__':
    args = parse_args()
    proxy = ProxyServer(args.port)
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        sys.exit(1)
