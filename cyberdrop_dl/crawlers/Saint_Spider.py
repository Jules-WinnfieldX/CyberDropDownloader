from yarl import URL

from ..base_functions.base_functions import log, logger, get_db_path, get_filename_and_ext
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class SaintCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Basic director for saint scraping"""
        album_obj = AlbumItem("Loose Saint Files", [])
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        try:
            soup = await session.get_BS4(url)
            link = URL(soup.select_one('video[id=main-video] source').get('src'))
            url_path = await get_db_path(link)
            complete = await self.SQL_Helper.check_complete_singular("saint", url_path)
            filename, ext = await get_filename_and_ext(link.name)
            media_item = MediaItem(link, url, complete, filename, ext, filename)
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("saint", url_path, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj
