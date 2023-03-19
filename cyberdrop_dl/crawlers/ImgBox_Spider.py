from yarl import URL

from ..base_functions.base_functions import (
    check_direct,
    get_filename_and_ext,
    log,
    logger,
    make_title_safe,
)
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class ImgBoxCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director func for ImgBox scraping"""
        album_obj = AlbumItem("Loose ImgBox Files", [])
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")

        try:
            if await check_direct(url):
                filename, ext = await get_filename_and_ext(url.name)
                complete = await self.SQL_Helper.check_complete_singular("imgbox", url)
                media_item = MediaItem(url, url, complete, filename, ext, filename)
                await album_obj.add_media(media_item)

            elif "g" in url.parts:
                title, images = await self.folder(session, url)
                if not title:
                    title = url.raw_name
                title = await make_title_safe(title)
                await album_obj.set_new_title(title)
                for img in images:
                    try:
                        filename, ext = await get_filename_and_ext(img.name)
                    except NoExtensionFailure:
                        logger.debug("Couldn't get extension for %s", str(img))
                        continue
                    complete = await self.SQL_Helper.check_complete_singular("imgbox", img)
                    media_item = MediaItem(img, url, complete, filename, ext, filename)
                    await album_obj.add_media(media_item)
            else:
                img = await self.singular(session, url)
                filename, ext = await get_filename_and_ext(img.name)
                complete = await self.SQL_Helper.check_complete_singular("imgbox", img)
                media_item = MediaItem(img, url, complete, filename, ext, filename)
                await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        await self.SQL_Helper.insert_album("imgbox", url, album_obj)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return album_obj

    async def folder(self, session: ScrapeSession, url: URL):
        """Gets links from a folder"""
        soup = await session.get_BS4(url)
        output = []
        title = soup.select_one("div[id=gallery-view] h1").get_text()

        images = soup.find('div', attrs={'id': 'gallery-view-content'})
        images = images.findAll("img")
        for link in images:
            link = link.get('src').replace("thumbs", "images").replace("_b", "_o")
            output.append(URL(link))

        return title, output

    async def singular(self, session: ScrapeSession, url: URL):
        """Gets individual links"""
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("img[id=img]").get('src'))
        return link
