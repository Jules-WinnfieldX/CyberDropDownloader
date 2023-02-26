from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class EHentaiCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for E-Hentai"""
        album_obj = AlbumItem("Loose EHentai Files", [])

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
        if "g" in url.parts:
            await self.get_album(session, url, album_obj)
        elif "s" in url.parts:
            await self.get_image(session, url, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        url_path = await get_db_path(url)
        await self.SQL_Helper.insert_album("e-hentai", url_path, album_obj)
        return album_obj

    async def get_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem):
        """Gets links from an album"""
        try:
            soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("h1[id=gn]").get_text())
            await album_obj.set_new_title(title)

            images = soup.select("div[class=gdtm] div a")
            for image in images:
                image = image.get('href')
                image = URL(image)
                await self.get_image(session, image, album_obj)

            next_page_opts = soup.select('td[onclick="document.location=this.firstChild.href"]')
            next_page = None
            for maybe_next in next_page_opts:
                if maybe_next.get_text() == ">":
                    next_page = maybe_next.select_one('a')
                    break
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    await self.get_album(session, next_page, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_image(self, session: ScrapeSession, url: URL, album_obj: AlbumItem):
        """Gets media items from image links"""
        try:
            soup = await session.get_BS4(url)
            image = soup.select_one("img[id=img]")
            link = URL(image.get('src'))

            url_path = await get_db_path(link, 'e-hentai')
            complete = await self.SQL_Helper.check_complete_singular("e-hentai", url_path)

            filename, ext = await get_filename_and_ext(link.name)
            media_item = MediaItem(link, url, complete, filename, ext, filename)
            await album_obj.add_media(media_item)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

