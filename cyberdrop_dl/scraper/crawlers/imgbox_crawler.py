from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem, MediaItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, log, get_download_path, get_filename_and_ext

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class ImgBoxCrawler:
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
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("imgbox")
        self.download_queue = await self.manager.queue_manager.get_download_queue("imgbox")

        self.client = self.manager.client_manager.scraper_session

    async def finish_task(self):
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

        if "t" in scrape_item.url.host or "_" in scrape_item.url.name:
            scrape_item.url = URL("https://imgbox.com") / scrape_item.url.name.split("_")[0]

        if "g" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("imgbox", scrape_item.url)

        title = soup.select_one("div[id=gallery-view] h1").get_text().rsplit(" - ", 1)[0] + f" ({scrape_item.url.host})"
        date = title.split(" UTC)")[0].split("(")[-1]

        scrape_item.possible_datetime = date
        scrape_item.part_of_album = True
        await scrape_item.add_to_parent_title(title)

        images = soup.find('div', attrs={'id': 'gallery-view-content'})
        images = images.findAll("img")
        for link in images:
            link = URL(link.get('src').replace("thumbs", "images").replace("_b", "_o"))
            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("imgbox", scrape_item.url)

        image = URL(soup.select_one("img[id=img]").get('src'))
        filename, ext = await get_filename_and_ext(image.name)
        await self.handle_file(image, scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        check_complete = await self.manager.db_manager.history_table.check_complete("imgbox", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "ImgBox")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)
