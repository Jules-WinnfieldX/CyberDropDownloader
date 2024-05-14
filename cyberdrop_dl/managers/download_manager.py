from __future__ import annotations

import asyncio
import contextlib
import shutil
from base64 import b64encode
from typing import TYPE_CHECKING

from cyberdrop_dl.utils.utilities import FILE_FORMATS, log_debug

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


class FileLock:
    """Is this necessary? No. But I want it."""
    def __init__(self):
        self._locked_files = {}

    async def check_lock(self, filename: str) -> None:
        """Checks if the file is locked"""
        try:
            await log_debug(f"Checking lock for {filename}", 40)
            await self._locked_files[filename].acquire()
            await log_debug(f"Lock for {filename} acquired", 40)
        except KeyError:
            await log_debug(f"Lock for {filename} does not exist", 40)
            self._locked_files[filename] = asyncio.Lock()
            await self._locked_files[filename].acquire()
            await log_debug(f"Lock for {filename} acquired", 40)

    async def release_lock(self, filename: str) -> None:
        """Releases the file lock"""
        with contextlib.suppress(KeyError, RuntimeError):
            await log_debug(f"Releasing lock for {filename}", 40)
            self._locked_files[filename].release()
            await log_debug(f"Lock for {filename} released", 40)


class DownloadManager:
    def __init__(self, manager: Manager):
        self.manager = manager
        self._download_instances: Dict = {}

        self.file_lock = FileLock()

        self.download_limits = {'bunkr': 1, 'bunkrr': 1, 'cyberdrop': 1, 'cyberfile': 1, "pixeldrain": 2}

    async def get_download_limit(self, key: str) -> int:
        """Returns the download limit for a domain"""
        if key in self.download_limits:
            instances = self.download_limits[key]
        else:
            instances = self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']

        if instances > self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']:
            instances = self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']
        return instances

    async def basic_auth(self, username, password) -> str:
        """Returns a basic auth token"""
        token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return f'Basic {token}'

    async def check_free_space(self) -> bool:
        """Checks if there is enough free space on the drive to continue operating"""
        free_space = shutil.disk_usage(self.manager.path_manager.download_dir.parent).free
        free_space_gb = free_space / 1024 ** 3
        return free_space_gb >= self.manager.config_manager.global_settings_data['General']['required_free_space']

    async def check_allowed_filetype(self, media_item: MediaItem) -> bool:
        """Checks if the file type is allowed to download"""
        if media_item.ext in FILE_FORMATS['Images'] and self.manager.config_manager.settings_data['Ignore_Options']['exclude_images']:
            return False
        if media_item.ext in FILE_FORMATS['Videos'] and self.manager.config_manager.settings_data['Ignore_Options']['exclude_videos']:
            return False
        if media_item.ext in FILE_FORMATS['Audio'] and self.manager.config_manager.settings_data['Ignore_Options']['exclude_audio']:
            return False
        if (self.manager.config_manager.settings_data['Ignore_Options']['exclude_other'] and
              media_item.ext not in FILE_FORMATS['Images'] and media_item.ext not in FILE_FORMATS['Videos'] and
              media_item.ext not in FILE_FORMATS['Audio']):
            return False
        return True
