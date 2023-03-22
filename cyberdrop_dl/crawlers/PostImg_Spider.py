import itertools
from http import HTTPStatus

from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class PostImgCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for PostImg scraping"""
        album_obj = AlbumItem("Loose PostImg Files", [])
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")

        try:
            if "gallery" in url.parts:
                content = await self.get_folder(session, url)
                for media_item in content:
                    await album_obj.add_media(media_item)
            else:
                media_item = await self.get_singular(session, url)
                await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        await self.SQL_Helper.insert_album("postimg", url, album_obj)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return album_obj

    async def get_folder(self, session: ScrapeSession, url: URL):
        """Handles folder scraping"""
        album = url.raw_name
        data = {"action": "list", "album": album}
        content = []
        for i in itertools.count(1):
            data_used = data
            data_used["page"] = i
            data_out = await session.post(URL("https://postimg.cc/json"), data_used)
            if data_out['status_code'] != HTTPStatus.OK or not data_out['images']:
                break
            for item in data_out['images']:
                referer = URL("https://postimg.cc/" + item[0])
                img = URL(item[4].replace(item[0], item[1]))

                try:
                    filename, ext = await get_filename_and_ext(img.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(img))
                    continue
                complete = await self.SQL_Helper.check_complete_singular("postimg", img)
                media_item = MediaItem(img, referer, complete, filename, ext, filename)

                content.append(media_item)
        return content

    async def get_singular(self, session: ScrapeSession, url: URL):
        """Handles singular folder scraping"""
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("a[id=download]").get('href').replace("?dl=1", ""))

        filename, ext = await get_filename_and_ext(link.name)
        complete = await self.SQL_Helper.check_complete_singular("postimg", link)
        media_item = MediaItem(link, url, complete, filename, ext, filename)

        return media_item
