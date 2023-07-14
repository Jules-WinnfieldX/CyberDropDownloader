from __future__ import annotations

import itertools
from http import HTTPStatus
from typing import TYPE_CHECKING, List

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class PostImgCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for PostImg scraping"""
        album_obj = AlbumItem("Loose PostImg Files", [])
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        try:
            if "gallery" in url.parts:
                content = await self.get_folder(session, url)
                for media_item in content:
                    await album_obj.add_media(media_item)
            elif url.host == "i.postimg.cc":
                url = URL("https://postimg.cc/") / url.parts[1]
                media_item = await self.get_singular(session, url)
                await album_obj.add_media(media_item)
            else:
                media_item = await self.get_singular(session, url)
                await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        await self.SQL_Helper.insert_album("postimg", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def get_folder(self, session: ScrapeSession, url: URL) -> List:
        """Handles folder scraping"""
        album = url.raw_name
        data = {"action": "list", "album": album, "page": 0}
        content = []
        for i in itertools.count(1):
            data["page"] = i
            data_out = await session.post(URL("https://postimg.cc/json"), data)
            if data_out['status_code'] != HTTPStatus.OK or not data_out['images']:
                break
            for item in data_out['images']:
                referer = URL("https://postimg.cc/" + item[0])
                img = URL(item[4].replace(item[0], item[1]))

                try:
                    media_item = await create_media_item(img, referer, self.SQL_Helper, "postimg")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", img)
                    continue

                content.append(media_item)
        return content

    async def get_singular(self, session: ScrapeSession, url: URL) -> MediaItem:
        """Handles singular folder scraping"""
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("a[id=download]").get('href').replace("?dl=1", ""))
        return await create_media_item(link, url, self.SQL_Helper, "postimg")
