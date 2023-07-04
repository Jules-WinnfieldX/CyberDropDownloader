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
from ..base_functions.error_classes import InvalidContentTypeFailure, NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class CyberdropCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.include_id = include_id
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Cyberdrop scraper"""
        album_obj = AlbumItem("Loose Cyberdrop Files", [])

        log(f"Starting: {url}", quiet=self.quiet, style="green")
        if await check_direct(url):
            if url.host.count(".") == 2:
                url = url.with_host(url.host.replace("cyberdrop.to", "cyberdrop.me"))
            media = await create_media_item(url, url, self.SQL_Helper, "cyberdrop")
            await album_obj.add_media(media)
            await self.SQL_Helper.insert_album("cyberdrop", URL(""), album_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
            return album_obj

        try:
            try:
                soup = await session.get_BS4(url)
            except InvalidContentTypeFailure:
                media = await create_media_item(url, url, self.SQL_Helper, "cyberdrop")
                await album_obj.add_media(media)
                await self.SQL_Helper.insert_album("cyberdrop", URL(""), album_obj)
                log(f"Finished: {url}", quiet=self.quiet, style="green")
                return album_obj

            title = soup.select_one("h1[id=title]").get_text()
            title = await make_title_safe(title)
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            await album_obj.set_new_title(title)

            links = soup.select('div[class="image-container column"] a')
            for link in links:
                link = URL(link.get('href'))
                if link.host.count(".") == 2:
                    link = link.with_host(link.host.replace("cyberdrop.to", "cyberdrop.me"))
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "cyberdrop")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue

                await album_obj.add_media(media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return album_obj

        await self.SQL_Helper.insert_album("cyberdrop", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj
