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


class ToonilyCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "toonily", "Toonily")
        self.primary_base_domain = URL("https://toonily.com")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "chapter" in scrape_item.url.name:
            await self.chapter(scrape_item)
        elif "webtoon" in scrape_item.url.parts:
            await self.series(scrape_item)
        else:
            await self.handle_direct_link(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def series(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        chapters = soup.select("li[class*=wp-manga-chapter] a")
        for chapter in chapters:
            chapter_path = chapter.get("href")
            if chapter_path.endswith("/"):
                chapter_path = chapter_path[:-1]
            if chapter_path.startswith("/"):
                chapter_path = self.primary_base_domain / chapter_path[1:]
            else:
                chapter_path = URL(chapter_path)
            new_scrape_item = await self.create_scrape_item(scrape_item, chapter_path, "", True)
            self.manager.task_group.create_task(self.run(new_scrape_item))

    @error_handling_wrapper
    async def chapter(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title_parts = soup.select_one("title").get_text().split(" - ")
        series_name = title_parts[0]
        chapter_title = title_parts[1]
        series_title = await self.create_title(series_name, None, None)
        await scrape_item.add_to_parent_title(series_title)
        await scrape_item.add_to_parent_title(chapter_title)

        scripts = soup.select("script")
        date = None
        for script in scripts:
            if "datePublished" in script.get_text():
                date = script.get_text().split("datePublished\":\"")[1].split("+")[0]
                date = await self.parse_datetime(date)
                break

        scrape_item.possible_datetime = date if date else scrape_item.possible_datetime
        scrape_item.part_of_album = True

        images = soup.select('div[class="page-break no-gaps"] img')
        for image in images:
            link = image.get("data-src")
            if not link:
                continue
            link = URL(link)

            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def handle_direct_link(self, scrape_item: ScrapeItem) -> None:
        """Handles a direct link"""
        scrape_item.url = scrape_item.url.with_name(scrape_item.url.name)
        filename, ext = await get_filename_and_ext(scrape_item.url.name)
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)


    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        return calendar.timegm(date.timetuple())

