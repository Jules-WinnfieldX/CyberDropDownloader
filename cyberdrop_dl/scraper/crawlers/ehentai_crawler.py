from __future__ import annotations

import calendar
import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class EHentaiCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "e-hentai", "E-Hentai")
        self.request_limiter = AsyncLimiter(10, 1)
        self.warnings_set = False

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "g" in scrape_item.url.parts:
            if not self.warnings_set:
                await self.set_no_warnings(scrape_item)
            await self.album(scrape_item)
        elif "s" in scrape_item.url.parts:
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

        title = await self.create_title(soup.select_one("h1[id=gn]").get_text(), None, None)
        date = await self.parse_datetime(soup.select_one("td[class=gdt2]").get_text())

        images = soup.select("div[class=gdtm] div a")
        for image in images:
            link = URL(image.get('href'))
            new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True, None, date)
            self.manager.task_group.create_task(self.run(new_scrape_item))

        next_page_opts = soup.select('td[onclick="document.location=this.firstChild.href"]')
        next_page = None
        for maybe_next in next_page_opts:
            if maybe_next.get_text() == ">":
                next_page = maybe_next.select_one('a')
                break
        if next_page is not None:
            next_page = URL(next_page.get('href'))
            if next_page is not None:
                new_scrape_item = await self.create_scrape_item(scrape_item, next_page, "")
                self.manager.task_group.create_task(self.run(new_scrape_item))

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)
        image = soup.select_one("img[id=img]")
        link = URL(image.get('src'))
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        if date.count(":") == 1:
            date = date + ":00"
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())

    @error_handling_wrapper
    async def set_no_warnings(self, scrape_item) -> None:
        """Sets the no warnings cookie"""
        self.warnings_set = True
        async with self.request_limiter:
            scrape_item.url = URL(str(scrape_item.url) + "/").update_query("nw=session")
            await self.client.get_BS4(self.domain, scrape_item.url)
