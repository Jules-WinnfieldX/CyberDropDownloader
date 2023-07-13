from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Tuple

import aiofiles
import rich
import yaml

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
    },
    'Text': {
        '.htm', '.html', '.md', '.nfo',
        '.txt',
    }
}

logger = logging.getLogger(__name__)
MAX_NAME_LENGTHS = {"FILE": 95, "FOLDER": 60}

async def clear() -> None:
    """Clears the terminal screen"""
    clear_screen_proc = await asyncio.create_subprocess_shell('cls' if os.name == 'nt' else 'clear')
    await clear_screen_proc.wait()


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
    title = title[:MAX_NAME_LENGTHS['FOLDER']].strip()
    return title


async def check_direct(url: URL) -> bool:
    """Checks whether the given url is a direct link to a content item"""
    mapping_direct = [r'i.pixl.li', r'i..pixl.li', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'jpg.church/images/...', r'simp..jpg.church', r'jpg.fish/images/...',
                      r'simp..jpg.fish', r'jpg.fishing/images/...', r'simp..jpg.fishing', r's..putmega.com',
                      r's..putme.ga', r'images..imgbox.com', r's..lovefap...', r'img.kiwi/images/',
                      r'thumbs.gfycat.com/', r'giant.gfycat.com/']
    return any(re.search(domain, str(url)) for domain in mapping_direct)


async def get_filename_and_ext(filename: str, forum: bool = False) -> Tuple[str, str]:
    """Returns the filename and extension of a given file, throws NoExtensionFailure if there is no extension"""
    filename_parts = filename.rsplit('.', 1)
    if len(filename_parts) == 1:
        raise NoExtensionFailure()
    if filename_parts[-1].isnumeric() and forum:
        filename_parts = filename_parts[0].rsplit('-', 1)
    ext = "." + filename_parts[-1].lower()
    filename = filename_parts[0][:MAX_NAME_LENGTHS['FILE']] if len(filename_parts[0]) > MAX_NAME_LENGTHS['FILE'] else filename_parts[0]
    filename = filename.strip()
    filename = await sanitize(filename + ext)
    return filename, ext


async def create_media_item(url: URL, referer: URL, sql_helper: SQLHelper, domain: str) -> MediaItem:
    """Returns the MediaItem of a given url, throws NoExtensionFailure if url.name doesn't have extension"""
    filename, ext = await get_filename_and_ext(url.name)
    complete = await sql_helper.check_complete_singular(domain, url)
    return MediaItem(url, referer, complete, filename, ext, filename)


class CacheManager:
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache = {}

    async def load(self):
        if not self.cache_file.exists():
            return

        async with aiofiles.open(self.cache_file, 'r') as cache_file:
            cache = yaml.load(await cache_file.read(), Loader=yaml.FullLoader)
        if cache:
            self.cache = cache

    async def get(self, key: str) -> Any:
        return self.cache.get(key, None)

    async def save(self, key: str, value: Any):
        self.cache[key] = value
        await self._save()

    async def remove(self, key: str):
        if key in self.cache:
            del self.cache[key]
            await self._save()

    async def _save(self):
        cache = yaml.dump(self.cache)
        async with aiofiles.open(self.cache_file, 'w') as cache_file:
            await cache_file.write(cache)


class ErrorFileWriter:
    """Writes errors to a file"""
    def __init__(self, output_errored: bool, output_unsupported: bool, output_last_post: bool, errored_scrapes: Path,
                 errored_downloads: Path, unsupported: Path, last_post: Path):
        self.output_errored = output_errored
        self.output_unsupported = output_unsupported
        self.output_last_post = output_last_post

        self.errored_scrapes = errored_scrapes
        self.errored_downloads = errored_downloads
        self.unsupported = unsupported
        self.last_post = last_post

    async def row_to_csv(self, row: list[str]) -> str:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(row)
        return output.getvalue()

    async def write_errored_scrape(self, url: URL, e: Exception, quiet: bool) -> None:
        """Writes to the error file"""
        log(f"Error: {url}", quiet=quiet, style="red")
        logger.debug(e)

        if not self.output_errored:
            return

        async with aiofiles.open(self.errored_scrapes, 'a') as f:
            line = await self.row_to_csv([f"{url}", f"{e}"])
            await f.write(line)

    async def write_errored_scrape_header(self):
        """Writes to the error file"""
        if not self.output_errored:
            return

        async with aiofiles.open(self.errored_scrapes, 'a') as f:
            await f.write("URL,Exception\n")

    async def write_errored_download(self, url: URL, referer: URL, error_message: str) -> None:
        """Writes to the error file"""
        if not self.output_errored:
            return

        async with aiofiles.open(self.errored_downloads, 'a') as f:
            line = await self.row_to_csv([f"{url}", f"{referer}", error_message])
            await f.write(line)

    async def write_errored_download_header(self):
        """Writes to the error file"""
        if not self.output_errored:
            return

        async with aiofiles.open(self.errored_downloads, 'a') as f:
            await f.write("URL,REFERER,REASON\n")

    async def write_unsupported(self, url: URL, referer: URL, title: str) -> None:
        """Writes to the error file"""
        if not self.output_unsupported:
            return

        async with aiofiles.open(self.unsupported, 'a') as f:
            line = await self.row_to_csv([f"{url}", f"{referer}", title])
            await f.write(line)

    async def write_unsupported_header(self):
        """Writes to the error file"""
        if not self.output_unsupported:
            return

        async with aiofiles.open(self.unsupported, 'a') as f:
            await f.write("URL,REFERER,TITLE\n")

    async def write_last_post(self, url: URL) -> None:
        """Writes to the error file"""
        if not self.output_last_post:
            return

        async with aiofiles.open(self.last_post, 'a') as f:
            line = await self.row_to_csv([f"{url}"])
            await f.write(line)
