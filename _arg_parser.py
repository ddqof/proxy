import argparse
from _defaults import __email__, __author__


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Simple http and https proxy.""",
        epilog=f"""Author:{__author__} <{__email__}>"""
    )

    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="Specify port number on which proxy server"
             " will receive connections.\nDefault is 8080."
    )

    return parser.parse_args()
