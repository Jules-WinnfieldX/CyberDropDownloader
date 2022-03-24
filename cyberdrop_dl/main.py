import asyncio
import logging
import os
from pathlib import Path
import re
import warnings

from colorama import Fore, Style
import nest_asyncio
import requests

from cyberdrop_dl import __version__ as VERSION
import cyberdrop_dl.settings as settings
from .utils.scraper import scrape
from .utils.downloaders import get_downloaders


# Fixes reactor already installed error (issue using Scrapy with Asyncio)
try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

logging.basicConfig(level=logging.DEBUG, filename='download.log',
                    format='%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s',
                    filemode='w')
warnings.filterwarnings("ignore", category=DeprecationWarning)

DOWNLOAD_FOLDER = settings.download_folder


def log(text, style):
    # Log function for printing to command line
    print(style + str(text) + Style.RESET_ALL)


def clear():
    # Clears command window
    os.system('cls' if os.name == 'nt' else 'clear')


def version_check() -> None:
    response = requests.get("https://api.github.com/repos/Jules-WinnfieldX/CyberDropDownloader/releases/latest")
    latest_version = response.json()["tag_name"]
    logging.debug(f"We are running version {VERSION} of Cyberdrop Downloader")
    if latest_version != VERSION:
        log("A new version of CyberDropDownloader is available\n"
            "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n", Fore.RED)
        input("To continue anyways press enter")
        clear()


def regex_links(urls) -> list:
    all_links = [x.group().replace(".md.", ".") for x in re.finditer(r"(?:http.*?)(?=('|$|\n|\r\n|\r|\s)|\")", urls)]
    return all_links


async def download_all():
    nest_asyncio.apply()
    clear()
    version_check()
    if os.path.isfile("URLs.txt"):
        log("URLs.txt exists", Fore.WHITE)
    else:
        f = open("URLs.txt", "w+")
        log("URLs.txt created", Fore.WHITE)
        exit()

    file_object = open("URLs.txt", "r")
    urls = file_object.read()
    urls = regex_links(urls)
    cookies, content_object = scrape(urls)
    if not content_object:
        logging.error(f'ValueError No links: {content_object}')
        raise ValueError('No links found, check the URL.txt\nIf the link works in your web browser, '
                         'please open an issue ticket with me.')
    clear()
    downloaders = get_downloaders(content_object, cookies=cookies, folder=Path(DOWNLOAD_FOLDER))

    for downloader in downloaders:
        await downloader.download_content()
    log('Finished scraping. Enjoy :)', Fore.WHITE)
    log('If you have ".download" files remaining, rerun this program. You most likely ran into download attempts limit',
        Fore.WHITE)


def main():
    asyncio.get_event_loop().run_until_complete(download_all())

if __name__ == '__main__':
    main()
