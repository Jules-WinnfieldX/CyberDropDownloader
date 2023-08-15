from asyncio import Queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict


class QueueManager:
    def __init__(self):
        self.scraper_queues: Dict = {}
        self.download_queues: Dict = {}
        self.url_objects_to_map = Queue()

    async def get_scraper_queue(self, key: str) -> Queue:
        if key not in self.scraper_queues:
            self.scraper_queues[key] = Queue()
        return self.scraper_queues[key]

    async def get_download_queue(self, key: str, limit: int) -> Queue:
        if key not in self.download_queues:
            self.download_queues[key] = Queue(limit)
        return self.download_queues[key]
