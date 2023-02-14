from yarl import URL

from ..base_functions.base_functions import log, logger, get_filename_and_ext, get_db_path, make_title_safe
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class PimpAndHostCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for pimpandhost scraping"""
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
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

        await self.SQL_Helper.insert_album("pimpandhost", url.path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
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
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
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
            url_path = await get_db_path(img)
            complete = await self.SQL_Helper.check_complete_singular("pimpandhost", url_path)
            media_item = MediaItem(img, url, complete, filename, ext)
            return media_item
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
