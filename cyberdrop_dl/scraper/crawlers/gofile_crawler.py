from __future__ import annotations

import http
import re
from copy import deepcopy
from dataclasses import field
from time import strftime, localtime
from typing import TYPE_CHECKING

import aiohttp.client_exceptions
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log, get_download_path, remove_id

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class GoFileCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.complete = False

        self.api_address = URL("https://api.gofile.io")
        self.js_address = URL("https://gofile.io/dist/js/alljs.js")
        self.token = ""
        self.websiteToken = ""

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("gofile")
        self.download_queue = await self.manager.queue_manager.get_download_queue("gofile")

        self.client = self.manager.client_manager.scraper_session

    async def finish_task(self) -> None:
        self.scraper_queue.task_done()
        if self.scraper_queue.empty():
            self.complete = True

    async def run_loop(self) -> None:
        """Runs the crawler loop"""
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            await log(f"Scrape Starting: {item.url}")
            if item.url in self.scraped_items:
                await self.finish_task()
                continue

            self.complete = False
            self.scraped_items.append(item.url)
            await self.fetch(item)

            await log(f"Scrape Finished: {item.url}")
            await self.finish_task()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        await self.get_token(self.client)
        await self.get_website_token(self.client)

        await self.album(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        content_id = scrape_item.url.name
        params = {
            "token": self.token,
            "contentId": content_id,
            "websiteToken": self.websiteToken,
        }
        try:
            async with self.request_limiter:
                JSON_Resp = await self.client.get_json("gofile", self.api_address / "getContent", params)
        except aiohttp.client_exceptions.ClientResponseError as e:
            if e.status == http.HTTPStatus.UNAUTHORIZED:
                self.websiteToken = ""
                self.manager.cache_manager.remove("gofile_website_token")
                await self.get_website_token(self.client)
                params["websiteToken"] = self.websiteToken
                async with self.request_limiter:
                    JSON_Resp = await self.client.get_json("gofile", self.api_address / "getContent", params)

        if JSON_Resp["status"] != "ok":
            raise Exception("Does Not Exist")

        JSON_Resp = JSON_Resp['data']
        title = JSON_Resp["name"] + f" ({scrape_item.url.host})"

        contents = JSON_Resp["contents"]
        for content_id in contents:
            content = contents[content_id]
            if content["type"] == "folder":
                new_scrape_item = ScrapeItem(scrape_item.url.with_name(content["name"]), scrape_item.parent_title, True)
                await new_scrape_item.add_to_parent_title(title)
                await self.scraper_queue.put(new_scrape_item)
                continue
            if content["link"] == "overloaded":
                link = URL(content["directLink"])
            else:
                link = URL(content["link"])
            filename, ext = await get_filename_and_ext(link.name)
            duplicate_scrape_item = deepcopy(scrape_item)
            duplicate_scrape_item.possible_datetime = content["createTime"]
            duplicate_scrape_item.part_of_album = True
            await duplicate_scrape_item.add_to_parent_title(title)
            await self.handle_file(link, duplicate_scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await remove_id(self.manager, filename, ext)

        check_complete = await self.manager.db_manager.history_table.check_complete("gofile", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "GoFile")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, original_filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @error_handling_wrapper
    async def get_token(self, session: ScraperClient) -> None:
        """Get the token for the API"""
        if self.token:
            return

        api_token = self.manager.config_manager.authentication_data["GoFile"]["gofile_api_key"]
        if api_token:
            self.token = api_token
            await self.set_cookie(session)
            return

        async with self.request_limiter:
            async with self.request_limiter:
                json_obj = await session.get_json("gofile", self.api_address / "createAccount")
            if json_obj["status"] == "ok":
                self.token = json_obj["data"]["token"]
                await self.set_cookie(session)
            else:
                raise Exception("Couldn't generate GoFile token")

    @error_handling_wrapper
    async def get_website_token(self, session: ScraperClient) -> None:
        """Creates an anon gofile account to use."""
        if self.websiteToken:
            return

        website_token = self.manager.cache_manager.get("gofile_website_token")
        if website_token:
            self.websiteToken = website_token
            return

        async with self.request_limiter:
            js_obj = await session.get_text("gofile", self.js_address)
        js_obj = str(js_obj)
        self.websiteToken = re.search(r'fetchData\.websiteToken\s*=\s*"(.*?)"', js_obj).group(1)
        if not self.websiteToken:
            raise Exception("Couldn't generate GoFile websiteToken")
        self.manager.cache_manager.save("gofile_website_token", self.websiteToken)

    async def set_cookie(self, session: ScraperClient) -> None:
        """Sets the given token as a cookie into the session (and client)"""
        client_token = self.token
        morsel: http.cookies.Morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.client_manager.cookies.update_cookies({'gofile.io': morsel})
