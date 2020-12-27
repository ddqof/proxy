#!/usr/bin/env python3

import asyncio
import sys
from proxy import ProxyServer
from restrict import RestrictedResource
from _arg_parser import parse_args

if __name__ == '__main__':
    args = parse_args()
    if "restricted_src" in args.__dict__:
        rsc = RestrictedResource(args.restricted_rsc, args.data_amount)
        proxy = ProxyServer(args.port, restricted_rsc=rsc)
    else:
        proxy = ProxyServer(args.port)
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        sys.exit(1)
