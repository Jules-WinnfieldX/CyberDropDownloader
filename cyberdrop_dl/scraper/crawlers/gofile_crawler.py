from __future__ import annotations

import http
import re
from copy import deepcopy
from typing import TYPE_CHECKING

import aiohttp.client_exceptions
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import ScrapeFailure, DownloadFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class GoFileCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "gofile", "GoFile")
        self.api_address = URL("https://api.gofile.io")
        self.js_address = URL("https://gofile.io/dist/js/alljs.js")
        self.token = ""
        self.websiteToken = ""
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        await self.get_token(self.api_address / "createAccount", self.client)
        await self.get_website_token(self.js_address, self.client)

        await self.album(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        content_id = scrape_item.url.name
        params = {
            "token": self.token,
            "contentId": content_id,
            "wt": self.websiteToken,
        }
        try:
            async with self.request_limiter:
                JSON_Resp = await self.client.get_json(self.domain, self.api_address / "getContent", params)
        except DownloadFailure as e:
            if e.status == http.HTTPStatus.UNAUTHORIZED:
                self.websiteToken = ""
                self.manager.cache_manager.remove("gofile_website_token")
                await self.get_website_token(self.js_address, self.client)
                params["wt"] = self.websiteToken
                async with self.request_limiter:
                    JSON_Resp = await self.client.get_json(self.domain, self.api_address / "getContent", params)

        if JSON_Resp["status"] != "ok":
            raise ScrapeFailure(404, "Does Not Exist")

        JSON_Resp = JSON_Resp['data']
        title = await self.create_title(JSON_Resp["name"], content_id, None)

        contents = JSON_Resp["contents"]
        for content_id in contents:
            content = contents[content_id]
            if content["type"] == "folder":
                new_scrape_item = await self.create_scrape_item(scrape_item, URL(content["name"]), title, True)
                self.manager.task_group.create_task(self.run(new_scrape_item))
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

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @error_handling_wrapper
    async def get_token(self, create_acct_address: URL, session: ScraperClient) -> None:
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
                JSON_Resp = await session.get_json(self.domain, create_acct_address)
            if JSON_Resp["status"] == "ok":
                self.token = JSON_Resp["data"]["token"]
                await self.set_cookie(session)
            else:
                raise ScrapeFailure(403, "Couldn't generate GoFile token")

    @error_handling_wrapper
    async def get_website_token(self, js_address: URL, session: ScraperClient) -> None:
        """Creates an anon gofile account to use."""
        if self.websiteToken:
            return

        website_token = self.manager.cache_manager.get("gofile_website_token")
        if website_token:
            self.websiteToken = website_token
            return

        async with self.request_limiter:
            text = await session.get_text(self.domain, js_address)
        text = str(text)
        self.websiteToken = re.search(r'fetchData\.wt\s*=\s*"(.*?)"', text).group(1)
        if not self.websiteToken:
            raise ScrapeFailure(403, "Couldn't generate GoFile websiteToken")
        self.manager.cache_manager.save("gofile_website_token", self.websiteToken)

    async def set_cookie(self, session: ScraperClient) -> None:
        """Sets the given token as a cookie into the session (and client)"""
        client_token = self.token
        morsel: http.cookies.Morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.client_manager.cookies.update_cookies({'gofile.io': morsel})
