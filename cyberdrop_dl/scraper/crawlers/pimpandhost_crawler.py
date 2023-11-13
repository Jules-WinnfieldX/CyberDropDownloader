from __future__ import annotations

import calendar
from dataclasses import field
from datetime import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log, get_download_path, remove_id

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class PimpAndHostCrawler:
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
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("pimpandhost")
        self.download_queue = await self.manager.queue_manager.get_download_queue("pimpandhost")

        self.client = self.manager.client_manager.scraper_session

    async def finish_task(self) -> None:
        self.scraper_queue.task_done()
        if self.scraper_queue.empty():
            self.complete = True

    async def run_loop(self) -> None:
        """Runs the crawler loop"""
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            await log(f"Scrape Starting: {item.url}")
            if item.url in self.scraped_items:
                await self.finish_task()
                continue

            self.complete = False
            self.scraped_items.append(item.url)
            await self.fetch(item)

            await log(f"Scrape Finished: {item.url}")
            await self.finish_task()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "album" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("pimpandhost", scrape_item.url)

        title = soup.select_one("span[class=author-header__album-name]").get_text()
        date = soup.select_one("span[class=date-time]").get("title")
        date = await self.parse_datetime(date)

        files = soup.select('a[class*="image-wrapper center-cropped im-wr"]')
        for file in files:
            link = URL(file.get("href"))
            new_scrape_item = ScrapeItem(link, scrape_item.parent_title, part_of_album=True, possible_datetime=date)
            await new_scrape_item.add_to_parent_title(title)
            await self.scraper_queue.put(new_scrape_item)

        next_page = soup.select_one("li[class=next] a")
        if next_page:
            next_page = next_page.get("href")
            if next_page.startswith("/"):
                next_page = URL("https://pimpandhost.com" + next_page)
            new_scrape_item = ScrapeItem(next_page, scrape_item.parent_title, part_of_album=True, possible_datetime=date)
            await self.scraper_queue.put(new_scrape_item)

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("pimpandhost", scrape_item.url)

        link = soup.select_one('.main-image-wrapper')
        link = link.get('data-src')
        link = URL("https:" + link) if link.startswith("//") else URL(link)

        date = soup.select_one("span[class=date-time]").get("title")
        date = await self.parse_datetime(date)

        new_scrape_item = ScrapeItem(link, scrape_item.parent_title, part_of_album=True, possible_datetime=date)
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, new_scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await remove_id(self.manager, filename, ext)

        check_complete = await self.manager.db_manager.history_table.check_complete("pimpandhost", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "PimpAndHost")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, original_filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime from a string"""
        date = datetime.strptime(date, '%A, %B %d, %Y %I:%M:%S%p %Z')
        return calendar.timegm(date.timetuple())
