from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class PimpAndHostCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for pimpandhost scraping"""
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        album_obj = AlbumItem("Loose Pixeldrain Files", [])

        if url.parts[1] == 'album':
            media_items, title = await self.get_listings(session, url)
            await album_obj.set_new_title(title)
            if media_items:
                for media_item in media_items:
                    await album_obj.add_media(media_item)
        else:
            media_item = await self.get_singular(session, url)
            await album_obj.add_media(media_item)

        await self.SQL_Helper.insert_album("pimpandhost", url, album_obj)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return album_obj

    async def get_listings(self, session: ScrapeSession, url: URL):
        """Handles album media"""
        media_items = []
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one("div[class=image-header]")
            user_link = title.select_one("span[class=details]")
            user_link.decompose()
            title = await make_title_safe(title.get_text())

            for file in soup.select('a[class*="image-wrapper center-cropped im-wr"]'):
                link = file.get("href")
                media_items.append(await self.get_singular(session, link))
            return media_items, title

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_singular(self, session: ScrapeSession, url: URL):
        """Handles singular files"""
        try:
            soup = await session.get_BS4(url)
            img = soup.select_one("a img")
            img = img.get("src")
            if img.startswith("//"):
                img = URL("https:" + img)
            filename, ext = await get_filename_and_ext(img.name)
            complete = await self.SQL_Helper.check_complete_singular("pimpandhost", img)
            media_item = MediaItem(img, url, complete, filename, ext, filename)
            return media_item
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
