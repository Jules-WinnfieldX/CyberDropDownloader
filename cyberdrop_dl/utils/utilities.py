from __future__ import annotations

import asyncio
import logging
import os
import re
import traceback
from enum import IntEnum
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

import rich
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure, FailedLoginFailure, InvalidContentTypeFailure

if TYPE_CHECKING:
    from typing import Tuple

    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem

logger = logging.getLogger("cyberdrop_dl")

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
        link = args[0] if isinstance(args[0], URL) else args[0].url

        try:
            return await func(self, *args, **kwargs)
        except NoExtensionFailure:
            await log(f"Scrape Failed: {link} (No File Extension)", 40)
            await self.manager.log_manager.write_scrape_error_log(link, " No File Extension")
            await self.manager.progress_manager.scrape_stats_progress.add_failure("No File Extension")
        except FailedLoginFailure:
            await log(f"Scrape Failed: {link} (Failed Login)", 40)
            await self.manager.log_manager.write_scrape_error_log(link, " Failed Login")
            await self.manager.progress_manager.scrape_stats_progress.add_failure("Failed Login")
        except InvalidContentTypeFailure:
            await log(f"Scrape Failed: {link} (Invalid Content Type Received)", 40)
            await self.manager.log_manager.write_scrape_error_log(link, " Invalid Content Type Received")
            await self.manager.progress_manager.scrape_stats_progress.add_failure("Invalid Content Type")
        except asyncio.TimeoutError:
            await log(f"Scrape Failed: {link} (Timeout)", 40)
            await self.manager.log_manager.write_scrape_error_log(link, " Timeout")
            await self.manager.progress_manager.scrape_stats_progress.add_failure("Timeout")
        except Exception as e:
            if hasattr(e, 'status'):
                if hasattr(e, 'message'):
                    await log(f"Scrape Failed: {link} ({e.status} - {e.message})", 40)
                    await self.manager.log_manager.write_scrape_error_log(link, f" {e.status} - {e.message}")
                else:
                    await log(f"Scrape Failed: {link} ({e.status})", 40)
                    await self.manager.log_manager.write_scrape_error_log(link, f" {e.status}")
                await self.manager.progress_manager.scrape_stats_progress.add_failure(e.status)
            else:
                await log(f"Scrape Failed: {link} ({e})", 40)
                await log(traceback.format_exc(), 40)
                await self.manager.log_manager.write_scrape_error_log(link, " See Log for Details")
                await self.manager.progress_manager.scrape_stats_progress.add_failure("Unknown")
    return wrapper


async def log(message: [str, Exception], level: int) -> None:
    """Simple logging function"""
    logger.log(level, message)


async def log_with_color(message: str, style: str, level: int) -> None:
    """Simple logging function with color"""
    logger.log(level, message)
    rich.print(f"[{style}]{message}[/{style}]")


"""~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


class CustomHTTPStatus(IntEnum):
    WEB_SERVER_IS_DOWN = 521
    IM_A_TEAPOT = 418
    DDOS_GUARD = 429


"""~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


async def sanitize(name: str) -> str:
    """Simple sanitization to remove illegal characters"""
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def sanitize_folder(title: str) -> str:
    """Simple sanitization to remove illegal characters from titles and trim the length to be less than 60 chars"""
    title = title.replace("\n", "").strip()
    title = title.replace("\t", "").strip()
    title = re.sub(' +', ' ', title)
    title = re.sub(r'[\\*?:"<>|/]', "-", title)
    title = re.sub(r'\.{2,}', ".", title)
    title = title.rstrip(".").strip()

    if "(" in title and ")" in title:
        new_title = title.rsplit("(")[0].strip()
        new_title = new_title[:MAX_NAME_LENGTHS['FOLDER']].strip()
        domain_part = title.rsplit("(")[1].strip()
        title = f"{new_title} ({domain_part}"
    else:
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


async def get_download_path(manager: Manager, scrape_item: ScrapeItem, domain: str) -> Path:
    """Returns the path to the download folder"""
    download_dir = manager.path_manager.download_dir

    if scrape_item.retry:
        return scrape_item.retry_path

    if scrape_item.parent_title and scrape_item.part_of_album:
        return download_dir / scrape_item.parent_title
    elif scrape_item.parent_title:
        return download_dir / scrape_item.parent_title / f"Loose Files ({domain})"
    else:
        return download_dir / f"Loose Files ({domain})"


async def remove_id(manager: Manager, filename: str, ext: str) -> Tuple[str, str]:
    """Removes the additional string some websites adds to the end of every filename"""
    original_filename = filename
    if manager.config_manager.settings_data["Download_Options"]["remove_generated_id_from_filenames"]:
        original_filename = filename
        filename = filename.rsplit(ext, 1)[0]
        filename = filename.rsplit("-", 1)[0]
        if ext not in filename:
            filename = filename + ext
    return original_filename, filename


"""~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


async def purge_dir(dirname: Path) -> None:
    """Purges empty directories"""
    deleted = []
    dir_tree = list(os.walk(dirname, topdown=False))

    for tree_element in dir_tree:
        sub_dir = tree_element[0]
        dir_count = len(os.listdir(sub_dir))
        if dir_count == 0:
            deleted.append(sub_dir)
    list(map(os.rmdir, deleted))


async def check_partials_and_empty_folders(manager: Manager):
    """Checks for partial downloads and empty folders"""
    if manager.config_manager.settings_data['Runtime_Options']['delete_partial_files']:
        await log_with_color("Deleting partial downloads...", "bold_red", 20)
        partial_downloads = manager.path_manager.download_dir.rglob("*.part")
        for file in partial_downloads:
            file.unlink(missing_ok=True)
    elif not manager.config_manager.settings_data['Runtime_Options']['skip_check_for_partial_files']:
        await log_with_color("Checking for partial downloads...", "yellow", 20)
        partial_downloads = any(f.is_file() for f in manager.path_manager.download_dir.rglob("*.part"))
        if partial_downloads:
            await log_with_color("There are partial downloads in the downloads folder", "yellow", 20)
        temp_downloads = any(Path(f).is_file() for f in await manager.db_manager.temp_table.get_temp_names())
        if temp_downloads:
            await log_with_color("There are partial downloads from the previous run, please re-run the program.", "yellow", 20)

    if not manager.config_manager.settings_data['Runtime_Options']['skip_check_for_empty_folders']:
        await log_with_color("Checking for empty folders...", "yellow", 20)
        await purge_dir(manager.path_manager.download_dir)
        if isinstance(manager.path_manager.sorted_dir, Path):
            await purge_dir(manager.path_manager.sorted_dir)


async def check_latest_pypi():
    """Checks if the current version is the latest version"""
    from cyberdrop_dl import __version__ as current_version
    import json
    import urllib.request

    # retrieve info on latest version
    contents = urllib.request.urlopen('https://pypi.org/pypi/cyberdrop-dl/json').read()
    data = json.loads(contents)
    latest_version = data['info']['version']

    if current_version.split(".")[0] > latest_version.split(".")[0]:
        return

    if current_version != latest_version:
        await log_with_color(f"New version of cyberdrop-dl available: {latest_version}", "bold_red", 30)
