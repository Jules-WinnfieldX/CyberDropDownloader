from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext, log

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class HotPicCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "hotpic", "HotPic")
        self.primary_base_domain = URL("https://hotpic.cc")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "album" in scrape_item.url.parts:
            await self.album(scrape_item)
        elif "i" in scrape_item.url.parts:
            await self.image(scrape_item)
        else:
            await log(f"Scrape Failed: Unknown URL Path for {scrape_item.url}", 40)
            await self.manager.progress_manager.scrape_stats_progress.add_failure("Unsupported Link")

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = await self.create_title(soup.select_one("title").text.rsplit(" - ")[0], scrape_item.url.parts[2], None)
        await scrape_item.add_to_parent_title(title)
        scrape_item.part_of_album = True

        files = soup.select("a[class*=spotlight]")
        for file in files:
            link = URL(file.get("href"))
            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        link = URL(soup.select_one("img[id*=main-image]").get("src"))
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)
