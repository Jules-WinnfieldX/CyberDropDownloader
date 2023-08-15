from asyncio import Queue
from dataclasses import field

from cyberdrop_dl.clients.download_client import DownloadClient
from cyberdrop_dl.managers.manager import Manager


class Downloader:
    def __init__(self, manager: Manager, domain: str):
        self.manager: Manager = manager
        self.domain: str = domain

        self.client: DownloadClient = field(init=False)
        self.download_queue: Queue = field(init=False)

    async def startup(self):
        self.download_queue = await self.manager.queue_manager.get_download_queue(self.domain, 0)
        self.client = await self.manager.client_manager.get_downloader_session(self.domain)

    async def run_loop(self):
        while True:
            pass
