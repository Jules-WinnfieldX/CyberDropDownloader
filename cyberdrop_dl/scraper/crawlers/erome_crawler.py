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

        title = await self.create_title(scrape_item.url.name, None, None)
        albums = soup.select('a[class=album-link]')

        for album in albums:
            link = URL(album['href'])
            new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
            self.manager.task_group.create_task(self.run(new_scrape_item))

        next_page = soup.select_one('a[rel="next"]')
        if next_page:
            next_page = next_page.get("href").split("page=")[-1]
            new_scrape_item = await self.create_scrape_item(scrape_item, scrape_item.url.with_query(f"page={next_page}"), "")
            self.manager.task_group.create_task(self.run(new_scrape_item))

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        album_id = scrape_item.url.parts[2]
        results = await self.get_album_results(album_id)
        
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        title_portion = soup.select_one('title').text.rsplit(" - Porn")[0].strip()
        if not title_portion:
            title_portion = scrape_item.url.name
        title = await self.create_title(title_portion, scrape_item.url.parts[2], None)
        await scrape_item.add_to_parent_title(title)

        images = soup.select('img[class="img-front lasyload"]')
        vidoes = soup.select('div[class=media-group] div[class=video-lg] video source')

        for image in images:
            link = URL(image['data-src'])
            filename, ext = await get_filename_and_ext(link.name)
            if not await self.check_album_results(link, results):
                await self.handle_file(link, scrape_item, filename, ext)

        for video in vidoes:
            link = URL(video['src'])
            filename, ext = await get_filename_and_ext(link.name)
            if not await self.check_album_results(link, results):
                await self.handle_file(link, scrape_item, filename, ext)
