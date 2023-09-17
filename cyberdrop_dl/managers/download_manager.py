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
        self.download_instances: Dict = {}
        self.download_instance_tasks: Dict = {}

    async def check_complete(self) -> bool:
        if not self.download_instances:
            return True
        for instance in self.download_instances.values():
            if not instance.complete:
                return False
        return True

    async def close(self) -> None:
        for downloader in self.download_instance_tasks.values():
            for task in downloader:
                task.cancel()

    async def get_download_instance(self, key: str, instances: int) -> Downloader:
        if key not in self.download_instances:
            self.download_instances[key] = Downloader(self.manager, key)
            await self.download_instances[key].startup()
            self.download_instance_tasks[key] = []
            for i in range(instances):
                task = asyncio.create_task(self.download_instances[key].run_loop())
        return self.download_instances[key]

    async def basic_auth(self, username, password) -> str:
        """Returns a basic auth token"""
        token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
        return f'Basic {token}'

    async def check_free_space(self) -> bool:
        """Checks if there is enough free space on the drive to continue operating"""
        free_space = shutil.disk_usage(self.manager.directory_manager.downloads.parent).free
        free_space_gb = free_space / 1024 ** 3
        return free_space_gb >= self.manager.config_manager.global_settings_data['General']['required_free_space']

    async def check_allowed_filetype(self, media_item: MediaItem) -> bool:
        """Checks if the file type is allowed to download"""
        if media_item.ext in FILE_FORMATS['images'] and self.manager.config_manager.global_settings_data['General']['exclude_images']:
            return False
        if media_item.ext in FILE_FORMATS['videos'] and self.manager.config_manager.global_settings_data['General']['exclude_videos']:
            return False
        if media_item.ext in FILE_FORMATS['audio'] and self.manager.config_manager.global_settings_data['General']['exclude_audio']:
            return False
        if media_item.ext in FILE_FORMATS['other'] and self.manager.config_manager.global_settings_data['General']['exclude_other']:
            return False
        return True
