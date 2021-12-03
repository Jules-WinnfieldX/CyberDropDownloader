import logging
import asyncio
from pathlib import Path
from utilities.scraper import scrape
from utilities.downloaders import get_downloaders
import settings
from colorama import Fore, Style
import requests
import os
import multiprocessing
import warnings
import readchar


logging.basicConfig(level=logging.DEBUG, filename='logs.log',
                    format='%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s',
                    filemode='w')
warnings.filterwarnings("ignore", category=DeprecationWarning)

SUPPORTED_URLS = {'cyberdrop.me', 'bunkr.is', 'pixl.is', 'putme.ga'}

CPU_COUNT = settings.threads if settings.threads != 0 else multiprocessing.cpu_count()
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
    current_version = "2.0.0"
    if latest_version != current_version:
        log("A new version of CyberDropDownloader is available\n"
            "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n", Fore.RED)
        input("To continue anyways press enter")
        clear()


async def main():
    clear()
    if os.path.isfile("URLs.txt"):
        log("URLs.txt exists", Fore.WHITE)
    else:
        f = open("URLs.txt", "w+")
        log("URLs.txt created", Fore.WHITE)
        exit()

    file_object = open("URLs.txt", "r")
    urls = [line for line in file_object]
    content_object = scrape(urls)
    if not content_object:
        logging.error(f'ValueError No links: {content_object}')
        raise ValueError('No links found, check the URL.txt')

    downloaders = get_downloaders(content_object, folder=Path(DOWNLOAD_FOLDER), max_workers=CPU_COUNT)

    for downloader in downloaders:
        await downloader.download_content()
    log('Finished scraping. Enjoy :)', Fore.WHITE)
    print(repr(readchar.readchar()))


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
