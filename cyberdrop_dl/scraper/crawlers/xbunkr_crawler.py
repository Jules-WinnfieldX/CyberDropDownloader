from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class XBunkrCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "xbunkr", "XBunkr")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "media" in scrape_item.url.host:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
            await self.handle_file(scrape_item.url, scrape_item, filename, ext)
        else:
            await self.album(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a profile"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = soup.select_one("h1[id=title]").text + f" ({scrape_item.url.host})"
        links = soup.select("a[class=image]")
        for link in links:
            link = URL(link.get('href'))
            try:
                filename, ext = await get_filename_and_ext(link.name)
            except NoExtensionFailure:
                await log(f"Couldn't get extension for {str(link)}")
                continue
            new_scrape_item = ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True)
            await new_scrape_item.add_to_parent_title(title)
            await self.handle_file(link, new_scrape_item, filename, ext)
