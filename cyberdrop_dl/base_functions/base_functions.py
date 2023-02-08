from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import aiofiles
import psutil as psutil
import rich
from yarl import URL

from cyberdrop_dl.base_functions.data_classes import MediaItem
from cyberdrop_dl.base_functions.error_classes import NoExtensionFailure

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
MAX_FILENAME_LENGTH = 100


async def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


async def log(text, quiet=False) -> None:
    """Logs to the output log file and optionally prints to the terminal with given style"""
    logger.debug(text)
    if not quiet:
        rich.print(str(text))


async def regex_links(urls: list) -> list:
    """Regex grab the links from the URLs.txt file"""
    """This allows code blocks or full paragraphs to be copy and pasted into the URLs.txt"""
    yarl_links = []
    for line in urls:
        if line.lstrip().startswith('#'):
            continue

        all_links = [x.group().replace(".md.", ".") for x in re.finditer(
            r"(?:http.*?)(?=($|\n|\r\n|\r|\s|\"|\[/URL]|]\[|\[/img]))", line)]
        for link in all_links:
            yarl_links.append(URL(link))
    return yarl_links


async def check_free_space(required_space: int, download_directory: Path) -> bool:
    """Checks if there is enough free space on the drive to continue operating"""
    free_space = psutil.disk_usage(str(download_directory.parent)).free
    free_space = ((free_space / 1024) / 1024) / 1024
    if required_space > free_space:
        return False
    else:
        return True


async def allowed_filetype(media: MediaItem, block_images: bool, block_video: bool, block_audio: bool, block_other: bool):
    ext = media.ext
    if block_images:
        if ext in FILE_FORMATS["Images"]:
            return False
    if block_video:
        if ext in FILE_FORMATS["Videos"]:
            return False
    if block_audio:
        if ext in FILE_FORMATS["Audio"]:
            return False
    if block_other:
        if ext not in FILE_FORMATS["Images"] and ext not in FILE_FORMATS["Videos"] and ext not in FILE_FORMATS["Audio"]:
            return False
    return True


async def purge_dir(dirname) -> None:
    """Purges empty directories"""
    deleted = []
    dir_tree = list(os.walk(dirname, topdown=False))

    for tree_element in dir_tree:
        sub_dir = tree_element[0]
        dir_count = len(os.listdir(sub_dir))
        if dir_count == 0:  # Helps with readability and i've had issues with it deleting non-empty dirs
            deleted.append(sub_dir)
    list(map(os.rmdir, deleted))


async def write_last_post_file(file: Path, url: str):
    """Writes the last post url from a thread to the specified file"""
    async with aiofiles.open(file, mode='a') as f:
        await f.write(url + '\n')
    return


async def get_db_path(url: URL):
    url_path = url.path
    if 'anonfiles' in url.host or 'bayfiles' in url.host:
        url_path = url.path
        url_path = url_path.split('/')
        url_path.pop(0)
        if len(url_path) > 1:
            url_path.pop(1)
        url_path = '/' + '/'.join(url_path)
    return url_path


async def sanitize(name: str) -> str:
    """Simple sanitization to remove illegal characters"""
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def make_title_safe(title: str) -> str:
    """Simple sanitization to remove illegal characters from titles and trim the length to be less than 60 chars"""
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    title = title[:60].rstrip()
    return title


async def check_direct(url: URL):
    mapping_direct = [r'i.pixl.li', r'i..pixl.li', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'jpg.church/images/...', r'simp..jpg.church', r's..putmega.com',
                      r's..putme.ga', r'images..imgbox.com']
    return any(re.search(domain, url.host) for domain in mapping_direct)


async def get_filename_and_ext(filename):
    filename_parts = filename.rsplit('.', 1)
    if len(filename_parts) == 1:
        raise NoExtensionFailure()
    ext = "." + filename_parts[-1].lower()
    filename = await sanitize(filename_parts[0] + ext)
    return filename, ext
