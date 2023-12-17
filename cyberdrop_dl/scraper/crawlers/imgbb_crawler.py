from __future__ import annotations

import calendar
import datetime
import re
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class ImgBBCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "imgbb", "ImgBB")
        self.primary_base_domain = URL("https://ibb.co")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if await self.check_direct_link(scrape_item.url):
            image_id = scrape_item.url.parts[1]
            scrape_item.url = self.primary_base_domain / image_id

        scrape_item.url = self.primary_base_domain / scrape_item.url.path[1:]
        if "album" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url / "sub")

        title = await self.create_title(soup.select_one("a[data-text=album-name]").get_text(), scrape_item.url.parts[2], None)
        albums = soup.select("a[class='image-container --media']")
        for album in albums:
            sub_album_link = URL(album.get('href'))
            new_scrape_item = await self.create_scrape_item(scrape_item, sub_album_link, title, True)
            self.manager.task_group.create_task(self.run(new_scrape_item))

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url / "sub")
        link_next = URL(soup.select_one("a[id=list-most-recent-link]").get("href"))

        while True:
            async with self.request_limiter:
                soup = await self.client.get_BS4(self.domain, link_next)
            links = soup.select("a[class*=image-container]")
            for link in links:
                link = URL(link.get('href'))
                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
                self.manager.task_group.create_task(self.run(new_scrape_item))

            link_next = soup.select_one('a[data-pagination=next]')
            if link_next is not None:
                link_next = link_next.get('href')
                if link_next is not None:
                    link_next = URL(link_next)
                else:
                    break
            else:
                break

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        link = URL(soup.select_one("div[id=image-viewer-container] img").get('src'))
        date = soup.select_one("p[class*=description-meta] span").get("title")
        date = await self.parse_datetime(date)
        scrape_item.possible_datetime = date

        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def handle_direct_link(self, scrape_item: ScrapeItem) -> None:
        """Handles a direct link"""
        scrape_item.url = scrape_item.url.with_name(scrape_item.url.name.replace('.md.', '.').replace('.th.', '.'))
        filename, ext = await get_filename_and_ext(scrape_item.url.name)
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())

    async def check_direct_link(self, url: URL) -> bool:
        """Determines if the url is a direct link or not"""
        mapping_direct = [r'i.ibb.co',]
        return any(re.search(domain, str(url)) for domain in mapping_direct)
