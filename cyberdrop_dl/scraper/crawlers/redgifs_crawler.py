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


class RedGifsCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "redgifs", "RedGifs")
        self.redgifs_api = URL("https://api.redgifs.com/")
        self.token = ""
        self.headers = {}
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if not self.token:
            await self.manage_token()

        if "users" in scrape_item.url.parts:
            await self.user(scrape_item)
        else:
            await self.post(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def user(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a users page"""
        print()

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a post"""
        print()

    @error_handling_wrapper
    async def media(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a media item"""
        print()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())

    async def manage_token(self) -> None:
        """Gets/Sets the redgifs token and header"""
        async with self.request_limiter:
            json_obj = await self.client.get_json(self.redgifs_api / "v2/auth/temporary")
        self.token = json_obj["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
