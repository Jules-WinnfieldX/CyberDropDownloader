from asyncio import Queue


class QueueManager:
    def __init__(self):
        self.scraper_queues: dict = {}
        self.download_queues: dict = {}

    async def get_scraper_queue(self, key: str) -> Queue:
        if key not in self.scraper_queues:
            self.scraper_queues[key] = Queue()
        return self.scraper_queues[key]

    async def get_download_queue(self, key: str, limit: int) -> Queue:
        if key not in self.download_queues:
            self.download_queues[key] = Queue(limit)
        return self.download_queues[key]
