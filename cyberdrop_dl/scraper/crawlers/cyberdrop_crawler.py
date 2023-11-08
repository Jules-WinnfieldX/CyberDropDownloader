from __future__ import annotations

import re
from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import InvalidContentTypeFailure
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem
from cyberdrop_dl.utils.utilities import (get_filename_and_ext, sanitize_folder, error_handling_wrapper, log,
                                          get_download_path, remove_id)

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem


class CyberdropCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.complete = False

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        download_limit = self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']

        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("cyberdrop")
        self.download_queue = await self.manager.queue_manager.get_download_queue("cyberdrop", download_limit)

        self.client = self.manager.client_manager.scraper_session

    async def run_loop(self) -> None:
        """Runs the crawler loop"""
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            await log(f"Scrape Starting: {item.url}")
            if item.url in self.scraped_items:
                continue

            self.complete = False
            self.scraped_items.append(item.url)
            await self.fetch(item)

            await log(f"Scrape Finished: {item.url}")
            self.scraper_queue.task_done()
            if self.scraper_queue.empty():
                self.complete = True

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        if self.check_direct_link(scrape_item.url):
            await self.handle_direct_link(scrape_item)
        else:
            await self.album(scrape_item)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem):
        """Scrapes an album"""
        try:
            soup = await self.client.get_BS4("cyberdrop", scrape_item.url)
        except InvalidContentTypeFailure:
            await self.handle_direct_link(scrape_item)
            return

        title = soup.select_one("h1[id=title]").get_text()
        title = await sanitize_folder(title)
        if scrape_item.parent_title:
            title = scrape_item.parent_title + " / " + title
        if self.manager.config_manager.settings_data['include_album_id_in_folder_name']:
            album_id = scrape_item.url.name
            title = title + " - " + album_id

        links = soup.select('div[class="image-container column"] a')
        for link in links:
            link = URL(link.get('href'))
            await self.scraper_queue.put(ScrapeItem(url=link, parent_title=title, part_of_album=True))

    @error_handling_wrapper
    async def handle_direct_link(self, scrape_item: ScrapeItem) -> None:
        """Handles a direct link"""
        filename, ext = await get_filename_and_ext(scrape_item.url.name)
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await remove_id(self.manager, filename, ext)
        url = url.with_host("cyberdrop.me")

        check_complete = await self.manager.db_manager.history_table.check_complete("cyberdrop", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "Cyberdrop")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, original_filename)
        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_direct_link(self, url: URL) -> bool:
        """Determines if the url is a direct link or not"""
        mapping_direct = [r'img-...cyberdrop...', r'f.cyberdrop...', r'fs-...cyberdrop...',]
        return any(re.search(domain, str(url)) for domain in mapping_direct)
