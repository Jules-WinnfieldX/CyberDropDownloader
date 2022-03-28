import logging
import os
import re
from urllib.parse import urljoin

from colorama import Fore, Style

"""This file contains generic information and functions that are used around the program"""

FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.gif', '.webp', '.jpe', '.svg',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg',
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a'
    },
    'Other': {
        '.json'
    }
}

mapping_ShareX = ["pixl.is", "putme.ga", "putmega.com", "jpg.church"]
mapping_Chibisafe = ["cyberdrop.me", "cyberdrop.cc", "cyberdrop.to", "cyberdrop.nl", "bunkr.is", "bunkr.to"]
mapping_Erome = ["erome.com"]
mapping_GoFile = ["gofile.io"]
mapping_Pixeldrain = ["pixeldrain.com"]

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 ' \
             'Safari/537.36'
MAX_FILENAME_LENGTH = 100

logger = logging.getLogger(__name__)


def sanitize(input: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", input)


def log(text, style = Fore.WHITE) -> None:
    """Wrapper around print() to add color to text"""
    print(style + str(text) + Style.RESET_ALL)


def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def make_title_safe(title: str):
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    return title


def bunkr_parse(url: str) -> str:
    """Fix the URL for bunkr.is."""
    extension = '.' + url.split('.')[-1]
    if extension.lower() in FILE_FORMATS['Videos']:
        changed_url = url.replace('cdn.bunkr', 'media-files.bunkr')
        changed_url = changed_url.replace('stream.bunkr.is/v/', 'media-files.bunkr.is/').split('/')
        changed_url = ''.join(map(lambda x: urljoin('/', x), changed_url))
        return changed_url
    if extension.lower() in FILE_FORMATS['Images']:
        changed_url = url.replace('i.bunkr', 'cdn.bunkr')
        return changed_url
    return url


def pixeldrain_parse(url: str, title: str) -> str:
    """Fix the URL for Pixeldrain"""
    if url.split('/')[-2] == 'l':
        final_url = f'https://pixeldrain.com/api/list/{title}/zip'
    else:
        final_url = f"https://pixeldrain.com/api/file/{title}?download"
    return final_url


def check_direct(url: str):
    mapping_direct = ['i.pixl.is', r's..putmega.com', r's..putme.ga', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'cdn.bunkr...', r'media-files.bunkr...', r'jpg.church/images/...']
    for domain in mapping_direct:
        if re.search(domain, url):
            return True
    return False
