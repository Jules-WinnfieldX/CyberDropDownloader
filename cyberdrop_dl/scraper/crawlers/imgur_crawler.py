from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, log, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class ImgurCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "imgur", "Imgur")
        self.imgur_api = URL("https://api.imgur.com/3/")
        self.imgur_client_id = self.manager.config_manager.authentication_data["Imgur"]["imgur_client_id"]
        self.imgur_client_remaining = 12500
        self.headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "i.imgur.com" in scrape_item.url.host:
            await self.handle_direct(scrape_item)
        elif "a" in scrape_item.url.parts:
            await self.album(scrape_item)
        else:
            await self.image(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        if self.imgur_client_id == "":
            await log("To scrape imgur content, you need to provide a client id")
            raise Exception("No Imgur Client ID provided")
        await self.check_imgur_credits()

        album_id = scrape_item.url.parts[-1]
        title = album_id + f" {scrape_item.url.host}"

        async with self.request_limiter:
            JSON_Obj = await self.client.get_json(self.domain, self.imgur_api / f"album/{album_id}", headers_inc=self.headers)
        if title in JSON_Obj["data"].keys():
            title = JSON_Obj["data"]["title"] + f" {scrape_item.url.host}"

        async with self.request_limiter:
            JSON_Obj = await self.client.get_json(self.domain, self.imgur_api / f"album/{album_id}/images", headers_inc=self.headers)

        for image in JSON_Obj["data"]:
            link = URL(image["link"])
            date = image["datetime"]
            new_scrape_object = ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True, possible_datetime=date)
            await new_scrape_object.add_to_parent_title(title)
            await self.handle_direct(new_scrape_object)

    @error_handling_wrapper
    async def image(self, scrape_item: ScrapeItem) -> None:
        if self.imgur_client_id == "":
            await log("To scrape imgur content, you need to provide a client id")
            raise Exception("No Imgur Client ID provided")
        await self.check_imgur_credits()

        image_id = scrape_item.url.parts[-1]
        async with self.request_limiter:
            JSON_Obj = await self.client.get_json(self.domain, self.imgur_api / f"image/{image_id}", headers_inc=self.headers)

        date = JSON_Obj["data"]["datetime"]
        link = URL(JSON_Obj["data"]["link"])
        new_scrape_object = ScrapeItem(url=link, parent_title=scrape_item.parent_title, possible_datetime=date)
        await self.handle_direct(new_scrape_object)

    @error_handling_wrapper
    async def handle_direct(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image"""
        filename, ext = await get_filename_and_ext(scrape_item.url.name)
        if ext.lower() == ".gifv" or ext.lower() == ".mp4":
            filename = filename.replace(ext, ".mp4")
            ext = ".mp4"
            scrape_item.url = URL("https://imgur.com/download") / filename.replace(ext, "")
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_imgur_credits(self) -> None:
        credits_obj = await self.client.get_json(self.domain, self.imgur_api / "credits", headers_inc=self.headers)
        self.imgur_client_remaining = credits_obj["data"]["ClientRemaining"]
        if self.imgur_client_remaining < 100:
            raise Exception("Imgur API rate limit reached")
