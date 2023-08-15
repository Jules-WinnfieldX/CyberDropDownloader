from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from cyberdrop_dl.downloader.downloader import Downloader

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager


class DownloadManager:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.download_instances: Dict = {}
        self.download_instance_tasks: Dict = {}

    async def close(self):
        for task in self.download_instance_tasks.values():
            task.cancel()

    async def get_download_instance(self, key: str) -> Downloader:
        if key not in self.download_instances:
            self.download_instances[key] = Downloader(self.manager, key)
            await self.download_instances[key].startup()
            task = asyncio.create_task(self.download_instances[key].run_loop())
            self.download_instance_tasks[key] = task
        return self.download_instances[key]
