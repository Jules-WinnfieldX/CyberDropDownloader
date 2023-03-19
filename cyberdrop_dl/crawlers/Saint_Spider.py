from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class SaintCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Basic director for saint scraping"""
        album_obj = AlbumItem("Loose Saint Files", [])
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")

        try:
            soup = await session.get_BS4(url)
            link = URL(soup.select_one('video[id=main-video] source').get('src'))
            complete = await self.SQL_Helper.check_complete_singular("saint", link)
            filename, ext = await get_filename_and_ext(link.name)
            media_item = MediaItem(link, url, complete, filename, ext, filename)
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("saint", link, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return album_obj
