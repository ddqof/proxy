import argparse

__author__ = "Dmitry Podaruev"
__email__ = "ddqof.vvv@gmail.com"


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
             " will receive connections."
    )

    return parser.parse_args()
