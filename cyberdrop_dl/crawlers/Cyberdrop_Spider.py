from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import (
    log,
    logger,
    make_title_safe, get_filename_and_ext,
)
from ..base_functions.data_classes import AlbumItem, MediaItem

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class CyberdropCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.include_id = include_id
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet
        self.limiter = AsyncLimiter(1.0, 2.0)

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Cyberdrop scraper"""
        album_obj = AlbumItem("Loose Cyberdrop Files", [])
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        try:
            if "a" in url.parts:
                await self.get_album(session, url, album_obj)
            else:
                await self.get_file(session, url, album_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        await self.SQL_Helper.insert_album("cyberdrop", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def get_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem) -> None:
        """Cyberdrop scraper"""
        async with self.limiter:
            soup = await session.get_BS4(url)
        title = await make_title_safe(soup.select_one("h1[id=title]").text)
        title = title.strip()
        await album_obj.set_new_title(title)

        links = soup.select("div[class*=image-container] a[id=file]")
        for link in links:
            link = link.get('href')
            if link.startswith("/"):
                link = URL("https://" + url.host + link)
            link = URL(link)
            await self.get_file(session, link, album_obj)

    async def get_file(self, session: ScrapeSession, url: URL, album_obj: AlbumItem) -> None:
        """Cyberdrop scraper"""
        url = URL("https://cyberdrop.me/api/") / url.path[1:]
        async with self.limiter:
            soup = await session.get_json(url)
        filename, ext = await get_filename_and_ext(soup["name"])
        link = URL(soup['url'])
        complete = await self.SQL_Helper.check_complete_singular("cyberdrop", link)
        media_item = MediaItem(link, url, complete, filename, ext, soup["name"])
        await album_obj.add_media(media_item)
