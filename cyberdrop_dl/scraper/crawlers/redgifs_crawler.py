from __future__ import annotations

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
        user_id = scrape_item.url.parts[-1].split(".")[0]

        page = 1
        total_pages = 1
        while page <= total_pages:
            async with self.request_limiter:
                JSON_Resp = await self.client.get_json(self.domain, (self.redgifs_api / "v2/users" / user_id / "search").with_query(f"order=new&count=40&page={page}"), headers_inc=self.headers)
            total_pages = JSON_Resp["pages"]
            gifs = JSON_Resp["gifs"]
            for gif in gifs:
                links = gif["urls"]
                date = gif["createDate"]
                title_part = gif["title"] if "title" in gif else "Loose Files"
                title = await self.create_title(title_part, None, None)

                try:
                    link = URL(links["hd"])
                except (KeyError, TypeError):
                    link = URL(links["sd"])

                filename, ext = await get_filename_and_ext(link.name)
                scrape_item.part_of_album = True
                scrape_item.possible_datetime = date
                await scrape_item.add_to_parent_title(title)
                await self.handle_file(link, scrape_item, filename, ext)
            page += 1

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a post"""
        post_id = scrape_item.url.parts[-1].split(".")[0]

        async with self.request_limiter:
            JSON_Resp = await self.client.get_json(self.domain, self.redgifs_api / "v2/gifs" / post_id, headers_inc=self.headers)

        title_part = JSON_Resp["gif"]["title"] if "title" in JSON_Resp["gif"] else "Loose Files"
        title = await self.create_title(title_part, None, None)
        links = JSON_Resp["gif"]["urls"]
        date = JSON_Resp["gif"]["createDate"]

        if "hd" in links:
            link = URL(links["hd"])
        else:
            link = URL(links["sd"])

        filename, ext = await get_filename_and_ext(link.name)
        scrape_item.part_of_album = True
        scrape_item.possible_datetime = date
        await scrape_item.add_to_parent_title(title)
        await self.handle_file(link, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def manage_token(self) -> None:
        """Gets/Sets the redgifs token and header"""
        async with self.request_limiter:
            json_obj = await self.client.get_json(self.domain, self.redgifs_api / "v2/auth/temporary")
        self.token = json_obj["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
