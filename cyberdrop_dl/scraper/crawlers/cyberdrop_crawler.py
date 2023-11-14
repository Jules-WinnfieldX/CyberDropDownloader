from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import InvalidContentTypeFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class CyberdropCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "cyberdrop", "Cyberdrop")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if self.check_direct_link(scrape_item.url):
            await self.handle_direct_link(scrape_item)
        else:
            await self.album(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            try:
                soup = await self.client.get_BS4(self.domain, scrape_item.url)
            except InvalidContentTypeFailure:
                await self.handle_direct_link(scrape_item)
                return

        title = soup.select_one("h1[id=title]").get_text()
        if self.manager.config_manager.settings_data['Download_Options']['include_album_id_in_folder_name']:
            album_id = scrape_item.url.name
            title = title + " - " + album_id
        await scrape_item.add_to_parent_title(title)

        links = soup.select('div[class="image-container column"] a')
        for link in links:
            link = URL(link.get('href'))
            await self.scraper_queue.put(ScrapeItem(url=link, parent_title=title, part_of_album=True))

    @error_handling_wrapper
    async def handle_direct_link(self, scrape_item: ScrapeItem) -> None:
        """Handles a direct link"""
        filename, ext = await get_filename_and_ext(scrape_item.url.name)
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_direct_link(self, url: URL) -> bool:
        """Determines if the url is a direct link or not"""
        mapping_direct = [r'img-...cyberdrop...', r'f.cyberdrop...', r'fs-...cyberdrop...',]
        return any(re.search(domain, str(url)) for domain in mapping_direct)
