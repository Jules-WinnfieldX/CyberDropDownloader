from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_db_path, get_filename_and_ext
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class XBunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for XBunkr scraping"""
        album_obj = AlbumItem("Loose XBunkr Files", [])

        try:
            if "media" in url.host:
                url_path = await get_db_path(url)
                complete = await self.SQL_Helper.check_complete_singular("xbunkr", url_path)
                filename, ext = await get_filename_and_ext(url.name)
                media_item = MediaItem(url, url, complete, filename, ext)
                await album_obj.add_media(media_item)

            else:
                soup = await session.get_BS4(url)
                links = soup.select("a[class=image]")
                title = await make_title_safe(soup.select_one("h1[id=title]").text)
                title = title.strip()
                await album_obj.set_new_title(title)
                for link in links:
                    link = URL(link.get('href'))
                    try:
                        filename, ext = await get_filename_and_ext(link.name)
                    except NoExtensionFailure:
                        logger.debug("Couldn't get extension for %s", str(link))
                        continue
                    url_path = await get_db_path(link)
                    complete = await self.SQL_Helper.check_complete_singular("xbunkr", url_path)
                    media_item = MediaItem(link, url, complete, filename, ext)
                    await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await self.SQL_Helper.insert_album("xbunkr", "", album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj
