from __future__ import annotations

import logging
import os
import re
import traceback
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

import rich
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure

if TYPE_CHECKING:
    from typing import Tuple

    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem

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
            if hasattr(e, 'status'):
                if hasattr(e, 'message'):
                    await log(f"Scrape Error: {args[0].url} ({e.status} - {e.message})")
                else:
                    await log(f"Scrape Error: {args[0].url} ({e.status})")
                await self.manager.progress_manager.scrape_stats_progress.add_failure(e.status)
            else:
                await log(f"Scrape Error: {args[0].url} ({e})")
                await log(traceback.format_exc())
                await self.manager.progress_manager.scrape_stats_progress.add_failure("Unknown")
    return wrapper


async def log(message: [str, Exception]) -> None:
    """Simple logging function"""
    logger.debug(message)


async def log_with_color(message: str, style: str) -> None:
    """Simple logging function with color"""
    logger.debug(message)
    rich.print(f"[{style}]{message}[/{style}]")


"""~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


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


async def get_download_path(manager: Manager, scrape_item: ScrapeItem, domain: str) -> Path:
    """Returns the path to the download folder"""
    if scrape_item.parent_title and scrape_item.part_of_album:
        return manager.directory_manager.downloads / scrape_item.parent_title
    elif scrape_item.parent_title:
        return manager.directory_manager.downloads / scrape_item.parent_title / f"Loose {domain} Files"
    else:
        return manager.directory_manager.downloads / f"Loose {domain} Files"


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
    if manager.config_manager.settings_data['Runtime_Options']['delete_partial_files']:
        await log_with_color("Deleting partial downloads...", "bold_red")
        partial_downloads = manager.directory_manager.downloads.rglob("*.part")
        for file in partial_downloads:
            file.unlink(missing_ok=True)
    elif not manager.config_manager.settings_data['Runtime_Options']['skip_check_for_partial_files']:
        await log_with_color("Checking for partial downloads...", "yellow")
        partial_downloads = any(f.is_file() for f in manager.directory_manager.downloads.rglob("*.part"))
        if partial_downloads:
            await log_with_color("There are partial downloads in the downloads folder", "yellow")
        temp_downloads = any(Path(f).is_file() for f in await manager.db_manager.temp_table.get_temp_names())
        if temp_downloads:
            await log_with_color("There are partial downloads from the previous run, please re-run the program.", "yellow")

    if not manager.config_manager.settings_data['Runtime_Options']['skip_check_for_empty_folders']:
        await log_with_color("Checking for empty folders...", "yellow")
        await purge_dir(manager.directory_manager.downloads)
        if isinstance(manager.directory_manager.sorted_downloads, Path):
            await purge_dir(manager.directory_manager.sorted_downloads)


async def check_latest_pypi():
    """Checks if the current version is the latest version"""
    import subprocess
    import sys
    import json
    import urllib.request

    # create dictionary of package versions
    pkgs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    keys = [p.decode().split('==')[0] for p in pkgs.split()]
    values = [p.decode().split('==')[1] for p in pkgs.split()]
    d = dict(zip(keys, values))

    # retrieve info on latest version
    contents = urllib.request.urlopen('https://pypi.org/pypi/cyberdrop-dl/json').read()
    data = json.loads(contents)
    latest_version = data['info']['version']

    if "cyberdrop-dl" not in d:
        return

    if d['cyberdrop-dl'] != latest_version:
        await log_with_color(f"New version of cyberdrop-dl available: {latest_version}", "bold_red")
