import asyncio
from asyncio import Queue
from dataclasses import field

from cyberdrop_dl.clients.scraper_client import ScraperClient
from cyberdrop_dl.managers.manager import Manager
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem


class BunkrCrawler:
    def __init__(self, manager: Manager):
        self.manager: Manager = manager
        self.client: ScraperClient = field(init=False)

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

    async def startup(self):
        download_limit = self.manager.config_manager.settings_data.get("max_simultaneous_downloads_per_domain")
        download_limit = 2 if download_limit > 2 else download_limit

        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("bunkr")
        self.download_queue = await self.manager.queue_manager.get_download_queue("bunkr", download_limit)

        self.client = await self.manager.client_manager.get_scraper_session("bunkr")

    async def run_loop(self):
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            if item.url in self.scraped_items:
                continue
            self.scraped_items.append(item.url)
            await self.fetch(item)

    async def fetch(self, scrape_item: ScrapeItem):
        pass
