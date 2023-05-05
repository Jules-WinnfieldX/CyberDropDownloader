from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Tuple

import rich

from cyberdrop_dl.base_functions.data_classes import MediaItem
from cyberdrop_dl.base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from pathlib import Path

    from yarl import URL
    
    from cyberdrop_dl.base_functions.sql_helper import SQLHelper


FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.gifv', '.webp', '.jpe', '.svg',
        '.jfif', '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg', '.mkv', '.mts', '.ts',
        '.f4v'
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a',
    }
}

logger = logging.getLogger(__name__)
MAX_FILENAME_LENGTH = 95


async def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def log(text: str, quiet: bool = False, style: str = "") -> None:
    """Logs to the output log file and optionally (by default) prints to the terminal with given style"""
    logger.debug(text)
    if not quiet:
        if style:
            text = f"[{style}]{text}[/{style}]"
        rich.print(text)


async def purge_dir(dirname: Path) -> None:
    """Purges empty directories"""
    deleted = []
    dir_tree = list(os.walk(dirname, topdown=False))

    for tree_element in dir_tree:
        sub_dir = tree_element[0]
        dir_count = len(os.listdir(sub_dir))
        if dir_count == 0:  # Helps with readability and i've had issues with it deleting non-empty dirs
            deleted.append(sub_dir)
    list(map(os.rmdir, deleted))


async def sanitize(name: str) -> str:
    """Simple sanitization to remove illegal characters"""
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def make_title_safe(title: str) -> str:
    """Simple sanitization to remove illegal characters from titles and trim the length to be less than 60 chars"""
    title = title.replace("\n", "").strip()
    title = title.replace("\t", "").strip()
    title = re.sub(' +', ' ', title)
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    title = title[:60].strip()
    return title


async def check_direct(url: URL) -> bool:
    """Checks whether the given url is a direct link to a content item"""
    mapping_direct = [r'i.pixl.li', r'i..pixl.li', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'jpg.church/images/...', r'simp..jpg.church', r's..putmega.com',
                      r's..putme.ga', r'images..imgbox.com', r's..lovefap...', r'img.kiwi/images/']
    return any(re.search(domain, str(url)) for domain in mapping_direct)


async def get_filename_and_ext(filename: str, forum: bool = False) -> Tuple[str, str]:
    """Returns the filename and extension of a given file, throws NoExtensionFailure if there is no extension"""
    filename_parts = filename.rsplit('.', 1)
    if len(filename_parts) == 1:
        raise NoExtensionFailure()
    if filename_parts[-1].isnumeric() and forum:
        filename_parts = filename_parts[0].rsplit('-', 1)
    ext = "." + filename_parts[-1].lower()
    filename = filename_parts[0][:MAX_FILENAME_LENGTH] if len(filename_parts[0]) > MAX_FILENAME_LENGTH else filename_parts[0]
    filename = filename.strip()
    filename = await sanitize(filename + ext)
    return filename, ext


async def create_media_item(url: URL, referer: URL, sql_helper: SQLHelper, domain: str) -> MediaItem:
    """Returns the MediaItem of a given url, throws NoExtensionFailure if url.name doesn't have extension"""
    filename, ext = await get_filename_and_ext(url.name)
    complete = await sql_helper.check_complete_singular(domain, url)
    return MediaItem(url, referer, complete, filename, ext, filename)
