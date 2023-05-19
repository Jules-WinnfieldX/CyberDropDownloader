from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger
from ..base_functions.data_classes import AlbumItem

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class SaintCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Basic director for saint scraping"""
        album_obj = AlbumItem("Loose Saint Files", [])
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        try:
            soup = await session.get_BS4(url)
            link = URL(soup.select_one('video[id=main-video] source').get('src'))
            media_item = await create_media_item(link, url, self.SQL_Helper, "saint")
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("saint", link, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj
