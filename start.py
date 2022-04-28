from cyberdrop_dl.main import main as main_dl
from cyberdrop_dl.main import parse_args
import sys


if __name__ == '__main__':
    print("""
    WAIT! If you're just trying to download files, check the README.md file for instructions.
    This file is intended for development usage ONLY.
    """)
    if input("Keep going? (y/N) ") == "y":
        args = parse_args()
        main_dl(args)
