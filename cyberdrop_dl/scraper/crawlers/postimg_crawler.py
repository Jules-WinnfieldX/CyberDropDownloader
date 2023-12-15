from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class PostImgCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "postimg", "PostImg")
        self.api_address = URL('https://postimg.cc/json')
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "i.postimg.cc" in scrape_item.url.host:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
            await self.handle_file(scrape_item.url, scrape_item, filename, ext)
        elif "gallery" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        data = {"action": "list", "album": scrape_item.url.raw_name, "page": 0}
        for i in itertools.count(1):
            data["page"] = i
            async with self.request_limiter:
                JSON_Resp = await self.client.post_data(self.domain, self.api_address, data=data)

            title = await self.create_title(scrape_item.url.raw_name, scrape_item.url.parts[2], None)

            for image in JSON_Resp['images']:
                link = URL(image[4])
                filename, ext = image[2], image[3]
                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
                await self.handle_file(link, new_scrape_item, filename, ext)

            if not JSON_Resp['has_page_next']:
                break

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        link = URL(soup.select_one("a[id=download]").get('href').replace("?dl=1", ""))
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)
