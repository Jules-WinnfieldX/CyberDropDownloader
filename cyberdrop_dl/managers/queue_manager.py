from asyncio import Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager


class QueueManager:
    def __init__(self, manager: 'Manager'):
        self.manager = manager
        self.scraper_queues: Dict = {}
        self.download_queues: Dict = {}
        self.url_objects_to_map = Queue()

    async def get_scraper_queue(self, key: str) -> Queue:
        """Returns a queue for a scraper session"""
        if key not in self.scraper_queues:
            self.scraper_queues[key] = Queue()
        return self.scraper_queues[key]

    async def get_download_queue(self, key: str) -> Queue:
        """Returns a queue for a download session"""
        if key not in self.download_queues:
            self.download_queues[key] = Queue(await self.manager.download_manager.get_download_limit(key))
        return self.download_queues[key]
