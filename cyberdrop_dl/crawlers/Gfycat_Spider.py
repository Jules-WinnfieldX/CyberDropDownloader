from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem
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
            await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
            soup = await session.get_BS4(url)

            video = soup.select_one("video[class='video media']")
            video_srcs = video.select("source")

            video_link = None
            for src in video_srcs:
                link = URL(src.get("src"))
                if "giant" in link.host:
                    video_link = link
                    break
            if video_link is None:
                video_link = URL(video_srcs[0].get("src"))

            complete = await self.SQL_Helper.check_complete_singular("gfycat", video_link)
            filename, ext = await get_filename_and_ext(video_link.name)
            media_item = MediaItem(video_link, url, complete, filename, ext, filename)
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("gfycat", video_link, album_obj)
            await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        return album_obj
