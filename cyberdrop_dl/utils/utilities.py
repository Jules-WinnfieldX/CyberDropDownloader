from __future__ import annotations

import logging
import re
from functools import wraps
from typing import TYPE_CHECKING

from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure

if TYPE_CHECKING:
    from typing import Tuple

    from cyberdrop_dl.managers.manager import Manager

logger = logging.getLogger(__name__)

MAX_NAME_LENGTHS = {"FILE": 95, "FOLDER": 60}

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


def error_handling_wrapper(func):
    """Wrapper handles errors for url scraping"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            await func(self, *args, **kwargs)
        except Exception as e:
            await handle_scrape_error(self.manager, args[0].url, e)
    return wrapper


async def sanitize(name: str) -> str:
    """Simple sanitization to remove illegal characters"""
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def sanitize_folder(title: str) -> str:
    """Simple sanitization to remove illegal characters from titles and trim the length to be less than 60 chars"""
    title = title.replace("\n", "").strip()
    title = title.replace("\t", "").strip()
    title = re.sub(' +', ' ', title)
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    title = title[:MAX_NAME_LENGTHS['FOLDER']].strip()
    return title


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
    filename = filename.rstrip(".")
    filename = await sanitize(filename + ext)
    return filename, ext


async def handle_scrape_error(manager: Manager, url: URL, error: Exception) -> None:
    """Handles logging scrape errors"""
    if hasattr(error, 'status'):
        if hasattr(error, 'message'):
            logger.debug(f"Scrape Error: {url} ({error.status} - {error.message})")
        else:
            logger.debug(f"Scrape Error: {url} ({error.status})")
        await manager.progress_manager.scrape_stats_progress.add_failure(error.status)
    else:
        logger.debug(f"Scrape Error: {url} ({error})")
        await manager.progress_manager.scrape_stats_progress.add_failure("Unknown")
