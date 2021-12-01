import logging
import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from utils.downloaders import get_downloaders
from utils.scrapers import get_scrapper
import settings

from colorama import Fore, Style
import requests
import os
import multiprocessing
from pathvalidate import sanitize_filename

logging.basicConfig(level=logging.DEBUG, filename='logs.log',
                    format='%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s')

SUPPORTED_URLS = {'cyberdrop.me', 'bunkr.is', 'pixl.is', 'putme.ga'}


FILE_FORMATS = {

    'Images': {
        '.jpg', '.jpeg', '.png', '.gif', '.gif', '.webp', '.jpe', '.svg', '.tif', '.tiff', '.jif',
    },

    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv', '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe', '.mp4', '.flv', '.mov', '.mpg', '.ogg'
    }
}

CPU_COUNT = settings.threads if settings.threads != 0 else multiprocessing.cpu_count()
DOWNLOAD_FOLDER = settings.download_folder

def log(text, style):
    # Log function for printing to command line
    print(style + str(text) + Style.RESET_ALL)


def clear():
    # Clears command window
    os.system('cls' if os.name == 'nt' else 'clear')


def classify_media_files(path: Path) -> None:

    images = [filename for filename in path.iterdir() if filename.suffix in FILE_FORMATS['Images']]

    videos = [filename for filename in path.iterdir() if filename.suffix in FILE_FORMATS['Videos']]

    if not images or not videos:
        return

    images_folder = Path(path / 'Images')
    images_folder.mkdir(exist_ok=True)
    videos_folder = Path(path / 'Videos')
    videos_folder.mkdir(exist_ok=True)

    # Move the images and videos to appropriate directories

    for image in images:
        image.rename(images_folder / image.name)
    for video in videos:
        video.rename(videos_folder / video.name)


def version_check() -> None:
    response = requests.get("https://api.github.com/repos/Jules-WinnfieldX/CyberDropDownloader/releases/latest")
    latest_version = response.json()["tag_name"]
    current_version = "1.5.7"
    if latest_version != current_version:
        log("A new version of CyberDropDownloader is available\n"
            "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n", Fore.RED)
        input("To continue anyways press enter")
        clear()


async def main():
    if os.path.isfile("URLs.txt"):
        log("URLs.txt exists", Fore.WHITE)
    else:
        f = open("URLs.txt", "w+")
        log("URLs.txt created", Fore.WHITE)

    file_object = open("URLs.txt", "r")
    urls = [line for line in file_object]
    for url in urls:
        scrapper = get_scrapper(url)

        with scrapper:
            title = sanitize_filename(scrapper.get_soup().select_one('title').text)
            links = scrapper.result_links()

            if not links:
                logging.error(f'ValueError No links: {links}')
                raise ValueError('No links found, check the URL.')

        downloaders = get_downloaders(links, folder=Path(
            title), max_workers=cpu_count)

        for downloader in downloaders:
            await downloader.download_content()
        classify_media_files(Path(title))


if __name__ == '__main__':
    asyncio.run(main())
