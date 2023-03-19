from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class HGameCGCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Basic director for HGameCG"""
        album_obj = AlbumItem("Loose HGamesCG Files", [])

        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        await self.get_album(session, url, album_obj)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        await self.SQL_Helper.insert_album("hgamecg", url, album_obj)
        return album_obj

    async def get_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem):
        """Handles album scraping, adds media items to the album_obj"""
        try:
            soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("div[class=navbar] h1").get_text())
            await album_obj.set_new_title(title)

            images = soup.select("div[class=image] a")
            for image in images:
                image = image.get('href')
                image = URL("https://" + url.host + image)
                link = await self.get_image(session, image)

                complete = await self.SQL_Helper.check_complete_singular("hgamecg", link)

                filename, ext = await get_filename_and_ext(link.name)
                media_item = MediaItem(link, image, complete, filename, ext, filename)
                await album_obj.add_media(media_item)

            next_page = soup.find("a", text="Next Page")
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL("https://" + url.host + next_page)
                    await self.get_album(session, next_page, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_image(self, session: ScrapeSession, url: URL):
        """Gets image link from the given url."""
        try:
            soup = await session.get_BS4(url)
            image = soup.select_one("div[class=hgamecgimage] img")
            image = URL(image.get('src'))
            return image
        except Exception:
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
