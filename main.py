#!/usr/bin/env python3

import asyncio
import sys
from proxy.config_handler import (get_restricted_list,
                                  get_black_list)
from proxy.proxy import ProxyServer
from _arg_parser import parse_args

if __name__ == '__main__':
    args = parse_args()
    proxy = ProxyServer(
        args.port,
        restricted=get_restricted_list(),
        black_list=get_black_list()
    )
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        sys.exit(1)
