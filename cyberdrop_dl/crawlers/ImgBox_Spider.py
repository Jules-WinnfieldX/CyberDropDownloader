from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import (
    check_direct,
    create_media_item,
    log,
    logger,
    make_title_safe,
)
from ..base_functions.data_classes import AlbumItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class ImgBoxCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director func for ImgBox scraping"""
        album_obj = AlbumItem("Loose ImgBox Files", [])
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        try:
            if await check_direct(url):
                media_item = await create_media_item(url, url, self.SQL_Helper, "imgbox")
                await album_obj.add_media(media_item)

            elif "g" in url.parts:
                title, images = await self.folder(session, url)
                if not title:
                    title = url.raw_name
                title = await make_title_safe(title)
                await album_obj.set_new_title(title)
                for img in images:
                    try:
                        media_item = await create_media_item(img, url, self.SQL_Helper, "imgbox")
                    except NoExtensionFailure:
                        logger.debug("Couldn't get extension for %s", img)
                        continue
                    await album_obj.add_media(media_item)
            else:
                img = await self.singular(session, url)
                media_item = await create_media_item(img, url, self.SQL_Helper, "imgbox")
                await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        await self.SQL_Helper.insert_album("imgbox", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def folder(self, session: ScrapeSession, url: URL):
        """Gets links from a folder"""
        soup = await session.get_BS4(url)
        output = []
        title = soup.select_one("div[id=gallery-view] h1").get_text()

        images = soup.find('div', attrs={'id': 'gallery-view-content'})
        images = images.findAll("img")
        for link in images:
            link = link.get('src').replace("thumbs", "images").replace("_b", "_o")
            output.append(URL(link))

        return title, output

    async def singular(self, session: ScrapeSession, url: URL) -> URL:
        """Gets individual links"""
        soup = await session.get_BS4(url)
        return URL(soup.select_one("img[id=img]").get('src'))
