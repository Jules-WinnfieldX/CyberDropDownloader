from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class AnonfilesCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.api_link = URL("https://api.anonfiles.com/v2/file")

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Scraper for Anonfiles"""
        assert url.host is not None
        if 'cdn' in url.host:
            url = URL("https://anonfiles.com") / url.parts[1]

        album_obj = AlbumItem("Loose Anon Files", [])

        log(f"Starting: {url}", quiet=self.quiet, style="green")

        try:
            json = await session.get_json(self.api_link/url.parts[1]/"info")
            if json['status']:
                soup = await session.get_BS4(url)

                link = soup.select_one("a[id=download-url]")
                link = URL(link.get('href'))

                complete = await self.SQL_Helper.check_complete_singular("anonfiles", link)

                filename, ext = await get_filename_and_ext(".".join(json['data']['file']['metadata']['name'].rsplit("_", 1)))
                media_item = MediaItem(link, url, complete, filename, ext, filename)
                await album_obj.add_media(media_item)
                if not complete:
                    await self.SQL_Helper.insert_media("anonfiles", "", media_item)
            else:
                log(f"Dead: {url}", quiet=self.quiet, style="red")

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return album_obj

        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj
