import argparse
import asyncio
import logging
import os
from pathlib import Path
import re

from colorama import Fore, Style
import nest_asyncio
import requests

from . import __version__ as VERSION
from .utils.scraper import scrape
from .utils.downloaders import get_downloaders


# Fixes reactor already installed error (issue using Scrapy with Asyncio)
try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

def parse_args():
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("-i", "--input-file", help="file containing links to download", default="URLs.txt")
    parser.add_argument("-o", "--output-folder", help="folder to download files to", default="Downloads")
    parser.add_argument("--log-file", help="log file to write to", default="downloader.log")
    parser.add_argument("--threads", type=int, help="number of threads to use (0 = max)", default=0)
    parser.add_argument("--attempts", type=int, help="number of attempts to download each file", default=10)
    parser.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    args = parser.parse_args()
    return args


def log(text, style = Fore.WHITE) -> None:
    """Wrapper around print() to add color to text"""
    print(style + str(text) + Style.RESET_ALL)


def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def version_check() -> None:
    response = requests.get("https://api.github.com/repos/Jules-WinnfieldX/CyberDropDownloader/releases/latest")
    latest_version = response.json()["tag_name"]
    logging.debug(f"We are running version {VERSION} of Cyberdrop Downloader")
    if latest_version != VERSION:
        log("A new version of CyberDropDownloader is available\n"
            "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n", Fore.RED)
        if input("Keep going? (Y/n) ") == "n":
            exit()
        clear()


def regex_links(urls) -> list:
    all_links = [x.group().replace(".md.", ".") for x in re.finditer(r"(?:http.*?)(?=('|$|\n|\r\n|\r|\s)|\")", urls)]
    return all_links


async def download_all(args: argparse.Namespace):
    nest_asyncio.apply()
    clear()
    version_check()
    logging.debug(f"Starting downloader with args: {args.__dict__}")
    input_file = Path(args.input_file)
    if not os.path.isfile(input_file):
        Path.touch(input_file)
        log(f"{input_file} created. Populate it and retry.")
        exit(1)

    links = args.links
    with open(input_file, "r") as f:
        links += regex_links(f.read())
    cookies, content_object = scrape(links, args.include_id)
    if not content_object:
        logging.error(f'ValueError No links: {content_object}')
        raise ValueError('No links found, check the URL.txt\nIf the link works in your web browser, '
                         'please open an issue ticket with me.')
    clear()
    downloaders = get_downloaders(content_object, cookies=cookies, folder=Path(args.output_folder), attempts=args.attempts, threads=args.threads)

    for downloader in downloaders:
        await downloader.download_content()
    log('Finished scraping. Enjoy :)')
    log('If you have ".download" files remaining, rerun this program. You most likely ran into download attempts limit')


def main():
    args = parse_args()
    logging.basicConfig(
        filename=args.log_file,
        level=logging.DEBUG,
        format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
        filemode="w"
    )
    asyncio.get_event_loop().run_until_complete(download_all(args))


if __name__ == '__main__':
    print("""
    STOP! If you're just trying to download files, check the README.md file for instructions.
    If you're developing this project, use start.py instead.
    """)
    exit()
