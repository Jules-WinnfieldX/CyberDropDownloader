from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, get_filename_and_ext, \
    get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure, InvalidContentTypeFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class CyberdropCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Cyberdrop scraper"""
        album_obj = AlbumItem("Loose Cyberdrop Files", [])

        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        if await check_direct(url):
            url_path = await get_db_path(url)
            complete = await self.SQL_Helper.check_complete_singular("cyberdrop", url_path)
            filename, ext = await get_filename_and_ext(url.name)
            media = MediaItem(url, url, complete, filename, ext, filename)
            await album_obj.add_media(media)
            await self.SQL_Helper.insert_album("cyberdrop", "", album_obj)
            await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
            return album_obj

        try:
            url_path = await get_db_path(url)
            try:
                soup = await session.get_BS4(url)
            except InvalidContentTypeFailure:
                url_path = await get_db_path(url)
                complete = await self.SQL_Helper.check_complete_singular("cyberdrop", url_path)
                filename, ext = await get_filename_and_ext(url.name)
                media = MediaItem(url, url, complete, filename, ext, filename)
                await album_obj.add_media(media)
                await self.SQL_Helper.insert_album("cyberdrop", "", album_obj)
                await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
                return album_obj

            title = soup.select_one("h1[id=title]").get_text()
            title = await make_title_safe(title.replace("\n", "").strip())
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            await album_obj.set_new_title(title)

            links = soup.select('div[class="image-container column"] a')
            for link in links:
                link = URL(link.get('href'))
                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue

                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("cyberdrop", url_path)
                media = MediaItem(link, url, complete, filename, ext, filename)
                await album_obj.add_media(media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return album_obj

        url_path = await get_db_path(url)
        await self.SQL_Helper.insert_album("cyberdrop", url_path, album_obj)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return album_obj
