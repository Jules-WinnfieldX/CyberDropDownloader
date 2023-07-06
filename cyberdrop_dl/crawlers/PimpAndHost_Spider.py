from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class PimpAndHostCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for pimpandhost scraping"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")
        album_obj = AlbumItem("Loose Pixeldrain Files", [])

        if url.parts[1] == 'album':
            media_items, title = await self.get_listings(session, url)
            await album_obj.set_new_title(title)
            if media_items:
                for media_item in media_items:
                    await album_obj.add_media(media_item)
        else:
            media_item = await self.get_singular(session, url)
            await album_obj.add_media(media_item)

        await self.SQL_Helper.insert_album("pimpandhost", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def get_listings(self, session: ScrapeSession, url: URL):
        """Handles album media"""
        media_items = []
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one("span[class=author-header__album-name]")
            title = await make_title_safe(title.get_text())

            for file in soup.select('a[class*="image-wrapper center-cropped im-wr"]'):
                link = URL(file.get("href"))
                media_items.append(await self.get_singular(session, link))

            next_page = soup.select_one("li[class=next] a")
            if next_page:
                next_page = next_page.get("href")
                if next_page.startswith("/"):
                    next_page = URL("https://pimpandhost.com" + next_page)
                next_page = URL(next_page)
                media_items_extended, throw = await self.get_listings(session, next_page)
                media_items.extend(media_items_extended)
            return media_items, title

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

    async def get_singular(self, session: ScrapeSession, url: URL):
        """Handles singular files"""
        try:
            soup = await session.get_BS4(url)
            img = soup.select_one("a img")
            img = img.get("src")
            if img.startswith("//"):
                img = URL("https:" + img)
            return await create_media_item(img, url, self.SQL_Helper, "pimpandhost")
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
