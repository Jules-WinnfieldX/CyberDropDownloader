from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class XBunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for XBunkr scraping"""
        album_obj = AlbumItem("Loose XBunkr Files", [])

        try:
            assert url.host is not None
            if "media" in url.host:
                media_item = await create_media_item(url, url, self.SQL_Helper, "xbunkr")
                await album_obj.add_media(media_item)

            else:
                soup = await session.get_BS4(url)
                links = soup.select("a[class=image]")
                title = await make_title_safe(soup.select_one("h1[id=title]").text)
                title = title.strip()
                await album_obj.set_new_title(title)
                for link in links:
                    link = URL(link.get('href'))
                    try:
                        media_item = await create_media_item(link, url, self.SQL_Helper, "xbunkr")
                    except NoExtensionFailure:
                        logger.debug("Couldn't get extension for %s", link)
                        continue
                    await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        await self.SQL_Helper.insert_album("xbunkr", URL(""), album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj
