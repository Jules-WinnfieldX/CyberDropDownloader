from yarl import URL

from ..base_functions.base_functions import log, logger, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class GfycatCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Basic scraper for gfycat"""
        try:
            album_obj = AlbumItem("Gfycat", [])
            await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
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

            url_path = await get_db_path(video_link)
            complete = await self.SQL_Helper.check_complete_singular("gfycat", url_path)
            filename, ext = await get_filename_and_ext(video_link.name)
            media_item = MediaItem(video_link, url, complete, filename, ext)
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("gfycat", url_path, album_obj)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return album_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return album_obj
