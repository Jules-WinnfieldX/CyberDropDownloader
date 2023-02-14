import http
from typing import Union

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class GoFileCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.api_address = URL("https://api.gofile.io")
        self.token = None

    async def get_token(self, session: ScrapeSession):
        """Creates an anon gofile account to use."""
        if self.token:
            return

        try:
            json_obj = await session.get_json(self.api_address / "createAccount")
            if json_obj["status"] == "ok":
                self.token = json_obj["data"]["token"]
                await self.set_cookie(session)
            else:
                raise
        except Exception as e:
            logger.debug("Error encountered while getting GoFile token", exc_info=True)
            await log(f"[red]Error: Couldn't generate GoFile token[/red]", quiet=self.quiet)
            logger.debug(e)

    async def set_cookie(self, session: ScrapeSession):
        """Sets the given token as a cookie into the session (and client)"""
        client_token = self.token
        morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.client_session.cookie_jar.update_cookies({'gofile.io': morsel})

    async def fetch(self, session: ScrapeSession, url: URL):
        """Basic director for actual scraping"""
        try:
            await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
            domain_obj = DomainItem("gofile", {})
            content_id = url.name
            results = await self.get_links(session, url, content_id, None)
            for title, media_item in results:
                await domain_obj.add_media(title, media_item)

            url_path = await get_db_path(url)
            await self.SQL_Helper.insert_domain("gofile", url_path, domain_obj)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return domain_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_links(self, session: ScrapeSession, url: URL, content_id: str, title=None):
        """Gets links from the given url, creates media_items"""
        results = []
        params = {
            "token": self.token,
            "contentId": content_id,
            "websiteToken": "12345",
        }
        content = await session.get_json_with_params(self.api_address / "getContent", params)
        if content["status"] != "ok":
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            return results

        content = content['data']
        if title:
            title = title + "/" + await make_title_safe(content["name"])
        else:
            title = await make_title_safe(content["name"])

        contents: dict[str, dict[str, Union[str, int]]] = content["contents"]
        sub_folders = []
        for val in contents.values():
            if val["type"] == "folder":
                sub_folders.append(val['code'])
            else:
                link = URL(val["link"]) if val["link"] != "overloaded" else URL(val["directLink"])
                try:
                    filename, ext = await get_filename_and_ext(val['name'])
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue
                link_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("gofile", link_path)
                media_item = MediaItem(link, url, complete, filename, ext)
                results.append([title, media_item])
        for sub_folder in sub_folders:
            results.extend(await self.get_links(session, url, sub_folder, title))
        return results
