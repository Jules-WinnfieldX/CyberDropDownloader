from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class FapelloCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "fapello", "Fapello")
        self.request_limiter = AsyncLimiter(5, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if not str(scrape_item.url).endswith("/"):
            scrape_item.url = URL(str(scrape_item.url) + "/")

        if scrape_item.url.parts[-2].isnumeric():
            await self.post(scrape_item)
        else:
            await self.profile(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def profile(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a profile"""
        async with self.request_limiter:
            soup, response_url = await self.client.get_BS4_and_return_URL(self.domain, scrape_item.url)
            if response_url != scrape_item.url:
                return

        title = await self.create_title(soup.select_one('h2[class="font-semibold lg:text-2xl text-lg mb-2 mt-4"]').get_text(), None, None)

        content = soup.select("div[id=content] a")
        for post in content:
            if "javascript" in post.get('href'):
                video_tag = post.select_one('iframe')
                video_link = URL(video_tag.get('src'))
                new_scrape_item = await self.create_scrape_item(scrape_item, video_link, "", True)
                await self.handle_external_links(new_scrape_item)
            else:
                link = URL(post.get('href'))
                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
                await self.handle_external_links(new_scrape_item)

        next_page = soup.select_one('div[id="next_page"] a')
        if next_page:
            next_page = next_page.get('href')
            if next_page:
                new_scrape_item = ScrapeItem(URL(next_page), scrape_item.parent_title)
                self.manager.task_group.create_task(self.run(new_scrape_item))

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

        content = soup.select_one('div[class="flex justify-between items-center"]')
        content_tags = content.select("img")
        content_tags.extend(content.select("source"))

        for selection in content_tags:
            link = URL(selection.get('src'))
            filename, ext = await get_filename_and_ext(link.name)
            await self.handle_file(link, scrape_item, filename, ext)
