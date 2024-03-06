from __future__ import annotations

import calendar
from datetime import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class PimpAndHostCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "pimpandhost", "PimpAndHost")
        self.request_limiter = AsyncLimiter(10, 1)

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
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = await self.create_title(soup.select_one("span[class=author-header__album-name]").get_text(), scrape_item.url.parts[2], None)
        date = soup.select_one("span[class=date-time]").get("title")
        date = await self.parse_datetime(date)

        files = soup.select('a[class*="image-wrapper center-cropped im-wr"]')
        for file in files:
            link = URL(file.get("href"))
            new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True, None, date)
            self.manager.task_group.create_task(self.run(new_scrape_item))

        next_page = soup.select_one("li[class=next] a")
        if next_page:
            next_page = next_page.get("href")
            if next_page.startswith("/"):
                next_page = URL("https://pimpandhost.com" + next_page)
            new_scrape_item = await self.create_scrape_item(scrape_item, next_page, "", True, None, date)
            self.manager.task_group.create_task(self.run(new_scrape_item))

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        link = soup.select_one('.main-image-wrapper')
        link = link.get('data-src')
        link = URL("https:" + link) if link.startswith("//") else URL(link)

        date = soup.select_one("span[class=date-time]").get("title")
        date = await self.parse_datetime(date)

        new_scrape_item = await self.create_scrape_item(scrape_item, link, "", True, None, date)
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, new_scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.strptime(date, '%A, %B %d, %Y %I:%M:%S%p %Z')
        return calendar.timegm(date.timetuple())
