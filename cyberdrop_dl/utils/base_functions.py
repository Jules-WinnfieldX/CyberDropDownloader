import logging
import os
import re
from urllib.parse import urljoin
import ssl

import certifi
from yarl import *
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
ssl_context = ssl.create_default_context(cafile=certifi.where())

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


def bunkr_parse(url: URL) -> URL:
    """Fix the URL for bunkr.is."""
    extension = '.' + str(url).split('.')[-1]
    if extension.lower() in FILE_FORMATS['Videos']:
        url = url.with_host('media-files.bunkr.is')
        return url
    if extension.lower() in FILE_FORMATS['Images']:
        url = url.with_host('cdn.bunkr.is')
        return url
    return url


def pixeldrain_parse(url: URL, title: str) -> URL:
    """Fix the URL for Pixeldrain"""
    if url.parts[1] == 'l':
        final_url = URL('https://pixeldrain.com/api/list/') / title / 'zip'
    else:
        final_url = (URL('https://pixeldrain.com/api/file/') / title).with_query('download')
    return final_url


def check_direct(url: URL):
    mapping_direct = ['i.pixl.is', r's..putmega.com', r's..putme.ga', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'cdn.bunkr...', r'media-files.bunkr...', r'jpg.church/images/...']
    for domain in mapping_direct:
        if re.search(domain, url.host):
            return True
    return False
