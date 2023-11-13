from __future__ import annotations

import re
from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import (FILE_FORMATS, get_filename_and_ext, error_handling_wrapper,
                                          log, get_download_path, remove_id)

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class BunkrCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.primary_base_domain = URL("https://bunkrr.su")

        self.complete = False

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("bunkr")
        self.download_queue = await self.manager.queue_manager.get_download_queue("bunkr")

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
        scrape_item.url = await self.get_stream_link(scrape_item.url)

        if "a" in scrape_item.url.parts:
            await self.album(scrape_item)
        elif "v" in scrape_item.url.parts:
            await self.video(scrape_item)
        else:
            await self.other(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
        for elem in title.find_all("span"):
            elem.decompose()
        title = title.get_text()
        await scrape_item.add_to_parent_title(title)

        card_listings = soup.select('div[class*="grid-images_box rounded-lg"]')
        for card_listing in card_listings:
            file = card_listing.select_one('a[class*="grid-images_box-link"]')
            date = card_listing.select_one('p[class*="date"]').text
            link = file.get("href")
            if link.startswith("/"):
                link = URL("https://" + scrape_item.url.host + link)
            link = URL(link)
            link = await self.get_stream_link(link)
            await self.scraper_queue.put(ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True, possible_datetime=await self.parse_datetime(date)))

    @error_handling_wrapper
    async def video(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a video"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        link_container = soup.select("a[class*=bg-blue-500]")[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def other(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image/other file"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        link_container = soup.select('a[class*="text-white inline-flex"]')[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await remove_id(self.manager, filename, ext)

        check_complete = await self.manager.db_manager.history_table.check_complete("bunkr", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "Bunkr")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, original_filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_stream_link(self, url: URL) -> URL:
        cdn_possibilities = r"^(?:(?:(?:media-files|cdn|c|pizza|cdn-burger)[0-9]{0,2})|(?:(?:big-taco-|cdn-pizza|cdn-meatballs)[0-9]{0,2}(?:redir)?))\.bunkr?\.[a-z]{2,3}$"

        if not re.match(cdn_possibilities, url.host):
            return url

        ext = url.suffix.lower()
        if ext == "":
            return url

        if ext in FILE_FORMATS['Images']:
            url = url.with_host(re.sub(r"^cdn(\d*)\.", r"i\1.", url.host))
        elif ext in FILE_FORMATS['Videos']:
            url = self.primary_base_domain / "v" / url.parts[-1]
        else:
            url = self.primary_base_domain / "d" / url.parts[-1]

        return url

    async def parse_datetime(self, date: str) -> str:
        time = date.split(" ")[0]
        day = date.split(" ")[1].split("/")[0]
        month = date.split(" ")[1].split("/")[1]
        year = date.split(" ")[1].split("/")[2]
        return f"{year}-{month}-{day} {time}"
