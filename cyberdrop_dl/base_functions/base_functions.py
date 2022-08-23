import logging
import os
import re

from colorama import Fore, Style
from yarl import URL

"""This file contains generic information and functions that are used around the program"""

FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.webp', '.jpe', '.svg',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg', '.mkv', '.mts', '.ts'
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a'
    },
    'Other': {
        '.json', '.torrent', '.zip', '.rar', '.7z', '.torrent'
    }
}

MAX_FILENAME_LENGTH = 100

logger = logging.getLogger(__name__)


async def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def log(text, style=Fore.WHITE) -> None:
    logger.debug(text)
    print(style + str(text) + Style.RESET_ALL)


async def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


async def make_title_safe(title: str):
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    return title


async def purge_dir(dirname, in_place=True):
    deleted = []
    dir_tree = list(os.walk(dirname, topdown=False))

    for tree_element in dir_tree:
        sub_dir = tree_element[0]
        dir_count = len(os.listdir(sub_dir))
        if dir_count == 0: # Helps with readability and i've had issues with it deleting non-empty dirs
            deleted.append(sub_dir)

    if in_place:
        list(map(os.rmdir, deleted))


async def regex_links(urls) -> list:
    all_links = [x.group().replace(".md.", ".") for x in re.finditer(
        r"(?:http.*?)(?=('|$|\n|\r\n|\r|\s|\"|\[/URL]|]\[|\[/img]))", urls)]
    yarl_links = []
    for link in all_links:
        yarl_links.append(URL(link))
    return yarl_links


async def cyberdrop_parse(url: URL) -> URL:
    mapping_direct = [r'img-...cyberdrop...',
                      r'f.cyberdrop...', r'fs-...cyberdrop...']
    url = str(url)
    for mapping in mapping_direct:
        url = re.sub(mapping, 'cyberdrop.to', url)
    return URL(url)


async def check_direct(url: URL):
    mapping_direct = ['i.pixl.is', r's..putmega.com', r's..putme.ga', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'cdn.bunkr...', r'cdn..bunkr...', r'media-files.bunkr...', r'jpg.church/images/...',
                      r'simp..jpg.church']
    return any(re.search(domain, url.host) for domain in mapping_direct)
