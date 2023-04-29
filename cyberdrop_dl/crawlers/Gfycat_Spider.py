from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger
from ..base_functions.data_classes import AlbumItem

if TYPE_CHECKING:
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class GfycatCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Basic scraper for gfycat"""
        album_obj = AlbumItem("Gfycat", [])
        try:
            log(f"Starting: {url}", quiet=self.quiet, style="green")
            soup = await session.get_BS4(url)

            video = soup.select_one("video[class='video media']")
            video_srcs = video.select("source")

            video_link = None
            for src in video_srcs:
                link = URL(src.get("src"))
                assert link.host is not None
                if "giant" in link.host:
                    video_link = link
                    break
            if video_link is None:
                video_link = URL(video_srcs[0].get("src"))

            media_item = await create_media_item(video_link, url, self.SQL_Helper, "gfycat")
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("gfycat", video_link, album_obj)
            log(f"Finished: {url}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

        return album_obj
