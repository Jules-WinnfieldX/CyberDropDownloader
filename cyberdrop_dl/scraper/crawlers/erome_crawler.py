from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class EromeCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "erome", "Erome")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "a" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.profile(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def profile(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a profile"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = scrape_item.url.name + f" ({scrape_item.url.host})"
        albums = soup.select('a[class=album-link]')

        for album in albums:
            link = URL(album['href'])
            new_scrape_item = ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True)
            await new_scrape_item.add_to_parent_title(title)
            await self.scraper_queue.put(new_scrape_item)

        next_page = soup.select_one('a[rel="next"]')
        if next_page:
            next_page = next_page.get("href").split("page=")[-1]
            new_scrape_item = ScrapeItem(url=scrape_item.url.with_query(f"page={next_page}"), parent_title=scrape_item.parent_title)
            await self.scraper_queue.put(new_scrape_item)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title = soup.select_one('div[class="col-sm-12 page-content"] h1').get_text()
        if not title:
            title = scrape_item.url.name
        await scrape_item.add_to_parent_title(title)

        images = soup.select('img[class="img-front lasyload"]')
        vidoes = soup.select('div[class=media-group] div[class=video-lg] video source')

        for image in images:
            link = URL(image['data-src'])
            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)

        for video in vidoes:
            link = URL(video['src'])
            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)
