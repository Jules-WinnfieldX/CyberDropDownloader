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


class LoveFapCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for lovefap scraping"""
        album_obj = AlbumItem("Loose LoveFap Files", [])

        log(f"Starting: {url}", quiet=self.quiet, style="green")
        if await check_direct(url):
            media = await create_media_item(url, url, self.SQL_Helper, "lovefap")
            await album_obj.add_media(media)
            await self.SQL_Helper.insert_album("lovefap", URL(""), album_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
            return album_obj

        try:
            if "video" in url.parts:
                await self.fetch_video(session, url, album_obj)
            else:
                await self.fetch_album(session, url, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return album_obj

        await self.SQL_Helper.insert_album("lovefap", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def fetch_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem) -> None:
        """Gets media_items for albums, and adds them to the Album_obj"""
        soup = await session.get_BS4(url)

        title = soup.select_one('div[class=albums-content-header] span[style*="float: left"]').get_text()
        if title is None:
            title = url.name
        title = await make_title_safe(title)
        await album_obj.set_new_title(title)

        links = soup.select('div[class="file picture"] a')
        links.extend(soup.select('div[class="file picture"] a'))
        for link in links:
            link = link.get('href')
            if link.startswith('/'):
                link = url.host + link
            link = URL(link)
            if "video" in link.parts:
                await self.fetch_video(session, url, album_obj)
            else:
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "lovefap")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue

                await album_obj.add_media(media)

    async def fetch_video(self, session: ScrapeSession, url: URL, album_obj: AlbumItem) -> None:
        """Gets media_items for video links"""
        soup = await session.get_BS4(url)
        video = soup.select_one("video[id=main-video] source")
        if video:
            link = URL(video.get("src"))
            try:
                media = await create_media_item(link, url, self.SQL_Helper, "lovefap")
            except NoExtensionFailure:
                logger.debug("Couldn't get extension for %s", link)
                return

            await album_obj.add_media(media)
