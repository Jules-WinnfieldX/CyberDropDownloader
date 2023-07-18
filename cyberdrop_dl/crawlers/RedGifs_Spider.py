from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class RedGifsCrawler:
    def __init__(self, separate_posts: bool, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.separate_posts = separate_posts
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.limiter = AsyncLimiter(10, 1)

        self.error_writer = error_writer

        self.redgifs_api = URL("https://api.redgifs.com/")
        self.token = ""
        self.headers = {}

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        domain_obj = DomainItem("redgifs", {})
        try:
            log(f"Starting: {url}", quiet=self.quiet, style="green")
            if not self.token:
                json_obj = await session.get_json(self.redgifs_api / "v2/auth/temporary")
                self.token = json_obj["token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}

            async with self.limiter:
                id = url.parts[-1] if url.parts[-1] != "" else url.parts[-2]
                id = id.split(".")[0]
                json_obj = await session.get_json(self.redgifs_api / "v2/gifs" / id, headers_inc=self.headers)
                links = json_obj["gif"]["urls"]
                if "hd" in links:
                    await self.get_image(URL(links["hd"]), url, "Loose Redgif Files", domain_obj)
                else:
                    await self.get_image(URL(links["sd"]), url, "Loose Redgif Files", domain_obj)

            await self.SQL_Helper.insert_domain("redgifs", url, domain_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return domain_obj

    async def get_image(self, url: URL, referer: URL, title: str, domain_obj: DomainItem):
        try:
            filename, ext = await get_filename_and_ext(url.name, True)
        except NoExtensionFailure:
            return domain_obj

        completed = await self.SQL_Helper.check_complete_singular("redgifs", url)
        media_item = MediaItem(url, referer, completed, filename, ext, filename)
        await domain_obj.add_media(title, media_item)
