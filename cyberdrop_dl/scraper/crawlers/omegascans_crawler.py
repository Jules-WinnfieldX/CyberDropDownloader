from __future__ import annotations

import calendar
import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import ScrapeFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext, log

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class OmegaScansCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "omegascans", "OmegaScans")
        self.primary_base_domain = URL("https://omegascans.org")
        self.api_url = "https://api.omegascans.org/chapter/query?page={}&perPage={}&series_id={}"
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "chapter" in scrape_item.url.name:
            await self.chapter(scrape_item)
        elif "series" in scrape_item.url.parts:
            await self.series(scrape_item)
        else:
            await self.handle_direct_link(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def series(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        scripts = soup.select("script")
        for script in scripts:
            if "series_id" in script.get_text():
                series_id = script.get_text().split('series_id\\":')[1].split(",")[0]
                break

        page_number = 1
        number_per_page = 30
        while True:
            api_url = URL(self.api_url.format(page_number, number_per_page, series_id))
            async with self.request_limiter:
                JSON_Obj = await self.client.get_json(self.domain, api_url)
            if not JSON_Obj:
                break

            for chapter in JSON_Obj['data']:
                chapter_url = scrape_item.url / chapter['chapter_slug']
                new_scrape_item = await self.create_scrape_item(scrape_item, chapter_url, "", True)
                self.manager.task_group.create_task(self.run(new_scrape_item))

            if JSON_Obj['meta']['current_page'] == JSON_Obj['meta']['last_page']:
                break
            page_number += 1

    @error_handling_wrapper
    async def chapter(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        if "This chapter is premium" in soup.get_text():
            await log("Scrape Failed: This chapter is premium", 40)
            raise ScrapeFailure(401, "This chapter is premium")

        title_parts = soup.select_one("title").get_text().split(" - ")
        series_name = title_parts[0]
        chapter_title = title_parts[1]
        series_title = await self.create_title(series_name, None, None)
        await scrape_item.add_to_parent_title(series_title)
        await scrape_item.add_to_parent_title(chapter_title)

        date = soup.select('h2[class="font-semibold font-sans text-muted-foreground text-xs"]')[-1].get_text()
        try:
            date = await self.parse_datetime_standard(date)
        except ValueError:
            scripts = soup.select("script")
            for script in scripts:
                if "created" in script.get_text():
                    date = script.get_text().split("created_at\\\":\\\"")[1].split(".")[0]
                    date = await self.parse_datetime_other(date)
                    break

        scrape_item.possible_datetime = date
        scrape_item.part_of_album = True

        images = soup.select("p[class*=flex] img")
        for image in images:
            link = image.get("src")
            if not link:
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

    async def parse_datetime_standard(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%m/%d/%Y")
        return calendar.timegm(date.timetuple())

    async def parse_datetime_other(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        return calendar.timegm(date.timetuple())

