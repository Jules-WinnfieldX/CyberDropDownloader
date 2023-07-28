from platformdirs import PlatformDirs

from cyberdrop_dl.main import main as main_dl
from cyberdrop_dl.main import parse_args


if __name__ == '__main__':
    print("""
    WAIT! If you're just trying to download files, check the README.md file for instructions.
    This file is intended for development usage ONLY.
    """)
    if input("Keep going? (y/N) ") == "y":
        app_dirs = PlatformDirs("Cyberdrop-DL")
        args = parse_args(app_dirs)
        main_dl(args)
