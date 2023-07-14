from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger, make_title_safe, create_media_item
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class ImgurCrawler:
    def __init__(self, separate_posts: bool, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter,
                 args: Dict[str, str]):
        self.separate_posts = separate_posts
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.limiter = AsyncLimiter(10, 1)

        self.error_writer = error_writer

        self.imgur_api = URL("https://api.imgur.com/3/")
        self.imgur_client_id = args["Authentication"]["imgur_client_id"]
        self.imgur_client_remaining = 12500
        self.headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Basic director for actual scraping"""
        domain_obj = DomainItem("imgur", {})
        try:
            log(f"Starting: {url}", quiet=self.quiet, style="green")

            if "a" in url.parts:
                if self.imgur_client_id == "":
                    log(f"To scrape imgur content, you need to provide a client id", quiet=self.quiet, style="green")
                    raise Exception("No Imgur Client ID provided")
                credits_obj, headers = await session.get_json_with_headers(self.imgur_api / "credits", headers_inc=self.headers)
                self.imgur_client_remaining = credits_obj["data"]["ClientRemaining"]
                if self.imgur_client_remaining < 100:
                    raise Exception("Imgur API rate limit reached")

                await self.get_album(session, url, domain_obj)
            elif "i.imgur.com" in url.host:
                await self.get_image(url, url, "Loose Imgur Files", domain_obj)

            await self.SQL_Helper.insert_domain("imgur", url, domain_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return domain_obj

    async def get_image(self, url: URL, referer: URL, title: str, domain_obj: DomainItem):
        try:
            filename, ext = await get_filename_and_ext(url.name, True)
        except NoExtensionFailure:
            logger.debug("Couldn't get extension for %s", url)
            return

        if ext.lower() == ".gifv" or ext.lower() == ".mp4":
            filename = filename.replace(ext, ".mp4")
            ext = ".mp4"
            url = URL("https://imgur.com/download") / filename.replace(ext, "")

        try:
            media_item = await create_media_item(url, referer, self.SQL_Helper, "imgur")
        except NoExtensionFailure:
            logger.debug("Couldn't get extension for %s", url)
            return
        await domain_obj.add_media(title, media_item)

    async def get_album(self, session: ScrapeSession, url: URL, domain_obj: DomainItem):
        album_id = url.parts[-1] if url.parts[-1] != "" else url.parts[-2]
        title = await make_title_safe(album_id + " (Imgur)")

        info_url = self.imgur_api / "album" / album_id
        album_info, headers = await session.get_json_with_headers(info_url, headers_inc=self.headers)
        self.imgur_client_remaining = int(headers['X-RateLimit-ClientRemaining'])
        if self.imgur_client_remaining < 100:
            raise Exception("Imgur API rate limit reached")
        if "title" in album_info['data'].keys():
            if album_info['data']['title']:
                title = await make_title_safe(album_info['data']['title'] + " (Imgur)")

        images_url = self.imgur_api / "album" / album_id / "images"
        images_info, headers = await session.get_json_with_headers(images_url, headers_inc=self.headers)
        self.imgur_client_remaining = int(headers['X-RateLimit-ClientRemaining'])
        if self.imgur_client_remaining < 100:
            raise Exception("Imgur API rate limit reached")
        for image in images_info['data']:
            media_url = URL(image['link'])
            await self.get_image(media_url, url, title, domain_obj)
