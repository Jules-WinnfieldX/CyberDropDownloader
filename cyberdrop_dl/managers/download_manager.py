from __future__ import annotations

import asyncio
import shutil
from base64 import b64encode
from typing import TYPE_CHECKING

from cyberdrop_dl.downloader.downloader import Downloader
from cyberdrop_dl.utils.utilities import FILE_FORMATS

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


class DownloadManager:
    def __init__(self, manager: Manager):
        self.manager = manager
        self._download_instances: Dict = {}
        self._download_instance_tasks: Dict = {}

        self.download_limits = {'bunkr': 1, 'cyberdrop': 1, 'coomer': 8, 'cyberfile': 2, 'kemono': 8, "pixeldrain": 2}

    async def check_complete(self) -> bool:
        """Checks if all download instances are complete"""
        if not self._download_instances:
            return True
        for instance in self._download_instances.values():
            if not instance.complete:
                return False
        return True

    async def close(self) -> None:
        """Closes all download instances"""
        for downloader in self._download_instance_tasks.values():
            for task in downloader:
                task.cancel()

    async def get_download_limit(self, key: str) -> int:
        """Returns the download limit for a domain"""
        if key in self.download_limits:
            instances = self.download_limits[key]
        else:
            instances = self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']

        if instances > self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']:
            instances = self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']
        return instances

    async def get_download_instance(self, key: str) -> Downloader:
        """Returns a download instance"""
        if key not in self._download_instances:
            self._download_instances[key] = Downloader(self.manager, key)
            await self._download_instances[key].startup()
            self._download_instance_tasks[key] = []
            for i in range(await self.get_download_limit(key)):
                self._download_instance_tasks[key].append(asyncio.create_task(self._download_instances[key].run_loop()))
        return self._download_instances[key]

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
        elif media_item.ext in FILE_FORMATS['Videos'] and self.manager.config_manager.settings_data['Ignore_Options']['exclude_videos']:
            return False
        elif media_item.ext in FILE_FORMATS['Audio'] and self.manager.config_manager.settings_data['Ignore_Options']['exclude_audio']:
            return False
        elif (self.manager.config_manager.settings_data['Ignore_Options']['exclude_other'] and
              media_item.ext not in FILE_FORMATS['Images'] and media_item.ext not in FILE_FORMATS['Videos'] and
              media_item.ext not in FILE_FORMATS['Audio']):
            return False
        return True
