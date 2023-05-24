from __future__ import annotations

import http
import re
from typing import TYPE_CHECKING, Union, List, Dict

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_filename_and_ext
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class GoFileCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.limiter = AsyncLimiter(1, 1)

        self.error_writer = error_writer

        self.api_address = URL("https://api.gofile.io")
        self.js_address = URL("https://gofile.io/dist/js/alljs.js")
        self.token = ""
        self.websiteToken = ""

    async def get_acct_token(self, session: ScrapeSession, api_token=None):
        """Creates an anon gofile account to use."""
        if self.token:
            return

        if api_token:
            self.token = api_token
            await self.set_cookie(session)
            return

        try:
            async with self.limiter:
                json_obj = await session.get_json(self.api_address / "createAccount")
            if json_obj["status"] == "ok":
                self.token = json_obj["data"]["token"]
                await self.set_cookie(session)
            else:
                raise
        except Exception as e:
            logger.debug("Error encountered while getting GoFile token", exc_info=True)
            log("Error: Couldn't generate GoFile token", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_website_token(self, session: ScrapeSession):
        """Creates an anon gofile account to use."""
        if self.websiteToken:
            return

        try:
            async with self.limiter:
                js_obj = await session.get_text(self.js_address)
            self.websiteToken = re.search(r'fetchData\.websiteToken\s*=\s*"(.*?)"', js_obj).group(1)
        except Exception as e:
            logger.debug("Error encountered while getting GoFile websiteToken", exc_info=True)
            log("Error: Couldn't generate GoFile websiteToken", quiet=self.quiet, style="red")
            logger.debug(e)

    async def set_cookie(self, session: ScrapeSession):
        """Sets the given token as a cookie into the session (and client)"""
        client_token = self.token
        morsel: http.cookies.Morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.client_session.cookie_jar.update_cookies({'gofile.io': morsel})

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Basic director for actual scraping"""
        domain_obj = DomainItem("gofile", {})
        try:
            log(f"Starting: {url}", quiet=self.quiet, style="green")
            content_id = url.name
            results = await self.get_links(session, url, content_id, None)
            for title, media_item in results:
                await domain_obj.add_media(title, media_item)

            await self.SQL_Helper.insert_domain("gofile", url, domain_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return domain_obj

    async def get_links(self, session: ScrapeSession, url: URL, content_id: str, title=None) -> List[List]:
        """Gets links from the given url, creates media_items"""
        results: List[List] = []
        params = {
            "token": self.token,
            "contentId": content_id,
            "websiteToken": self.websiteToken,
        }

        async with self.limiter:
            content = await session.get_json(self.api_address / "getContent", params)

        if content["status"] != "ok":
            await self.error_writer.write_errored_scrape(url, Exception("Does Not Exist"), self.quiet)
            return results

        content = content['data']
        if title:
            title = title + "/" + await make_title_safe(content["name"])
        else:
            title = await make_title_safe(content["name"])

        contents: Dict[str, Dict[str, Union[str, int]]] = content["contents"]
        sub_folders = []
        for val in contents.values():
            if val["type"] == "folder":
                sub_folders.append(val['code'])
            else:
                assert isinstance(val['name'], str)
                if val["link"] == "overloaded":
                    assert isinstance(val["directLink"], str)
                    link = URL(val["directLink"])
                else:
                    assert isinstance(val["link"], str)
                    link = URL(val["link"])
                try:
                    filename, ext = await get_filename_and_ext(val['name'])
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue
                complete = await self.SQL_Helper.check_complete_singular("gofile", link)
                media_item = MediaItem(link, url, complete, filename, ext, filename)
                results.append([title, media_item])
        for sub_folder in sub_folders:
            assert isinstance(sub_folder, str)
            results.extend(await self.get_links(session, url, sub_folder, title))
        return results
