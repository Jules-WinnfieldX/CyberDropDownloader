from __future__ import annotations

import calendar
import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class ImgBoxCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "imgbox", "ImgBox")
        self.primary_base_domain = URL("https://imgbox.com")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "t" in scrape_item.url.host or "_" in scrape_item.url.name:
            scrape_item.url = self.primary_base_domain / scrape_item.url.name.split("_")[0]
            
        if "gallery/edit" in str(scrape_item.url):
            scrape_item.url = self.primary_base_domain / "g" / scrape_item.url.parts[-2]

        if "g" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = await self.create_title(soup.select_one("div[id=gallery-view] h1").get_text().strip().rsplit(" - ", 1)[0], scrape_item.url.parts[2], None)

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
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        image = URL(soup.select_one("img[id=img]").get('src'))
        filename, ext = await get_filename_and_ext(image.name)
        await self.handle_file(image, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())
