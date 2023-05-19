from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class HGameCGCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Basic director for HGameCG"""
        album_obj = AlbumItem("Loose HGamesCG Files", [])

        log(f"Starting: {url}", quiet=self.quiet, style="green")
        await self.get_album(session, url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        await self.SQL_Helper.insert_album("hgamecg", url, album_obj)
        return album_obj

    async def get_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem) -> None:
        """Handles album scraping, adds media items to the album_obj"""
        try:
            soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("div[class=navbar] h1").get_text())
            await album_obj.set_new_title(title)

            images = soup.select("div[class=image] a")
            for image in images:
                image = image.get('href')
                assert url.host is not None
                image = URL("https://" + url.host + image)
                link = await self.get_image(session, image)

                media_item = await create_media_item(link, image, self.SQL_Helper, "hgamecg")
                await album_obj.add_media(media_item)

            next_page = soup.find("a", text="Next Page")
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    assert url.host is not None
                    next_page = URL("https://" + url.host + next_page)
                    await self.get_album(session, next_page, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

    async def get_image(self, session: ScrapeSession, url: URL) -> URL:
        """Gets image link from the given url."""
        try:
            soup = await session.get_BS4(url)
            image = soup.select_one("div[class=hgamecgimage] img")
            return URL(image.get('src'))
        except Exception:
            log(f"Error: {url}", quiet=self.quiet, style="red")
            return URL()
