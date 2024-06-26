from __future__ import annotations

import calendar
import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from mediafire import MediaFireApi, api
from yarl import URL

from cyberdrop_dl.clients.errors import ScrapeFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class MediaFireCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "mediafire", "mediafire")
        self.api = MediaFireApi()
        self.request_limiter = AsyncLimiter(5, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "folder" in scrape_item.url.parts:
            await self.folder(scrape_item)
        else:
            await self.file(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def folder(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a folder of media"""
        folder_key = scrape_item.url.parts[2]
        folder_details = self.api.folder_get_info(folder_key=folder_key)

        title = await self.create_title(folder_details['folder_info']['name'], folder_key, None)

        chunk = 1
        chunk_size = 100
        while True:
            try:
                folder_contents = self.api.folder_get_content(folder_key=folder_key, content_type='files', chunk=chunk, chunk_size=chunk_size)
            except api.MediaFireConnectionError:
                raise ScrapeFailure(500, "MediaFire connection closed")
            files = folder_contents['folder_content']['files']

            for file in files:
                date = await self.parse_datetime(file['created'])
                link = URL(file['links']['normal_download'])
                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True, None, date)
                self.manager.task_group.create_task(self.run(new_scrape_item))

            if folder_contents["folder_content"]["more_chunks"] == "yes":
                chunk += 1
            else:
                break

    @error_handling_wrapper
    async def file(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a single file"""
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        date = await self.parse_datetime(soup.select('ul[class=details] li span')[-1].get_text())
        scrape_item.possible_datetime = date
        link = URL(soup.select_one('a[id=downloadButton]').get('href'))
        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""
    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())
