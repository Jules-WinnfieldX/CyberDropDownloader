from __future__ import annotations

from typing import TYPE_CHECKING, List

from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class PixelDrainCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.api = URL('https://pixeldrain.com/api/')

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Director for pixeldrain scraping"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")
        album_obj = AlbumItem("Loose Pixeldrain Files", [])

        identifier = str(url).split('/')[-1]
        if url.parts[1] == 'l':
            await album_obj.set_new_title(url.name)
            media_items = await self.get_listings(session, identifier, url)
            for media_item in media_items:
                await album_obj.add_media(media_item)
        else:
            link = await self.create_download_link(identifier)
            complete = await self.SQL_Helper.check_complete_singular("pixeldrain", link)
            filename, ext = await get_filename_and_ext(await self.get_file_name(session, identifier))
            media_item = MediaItem(link, url, complete, filename, ext, filename)
            await album_obj.add_media(media_item)

        await self.SQL_Helper.insert_album("pixeldrain", url, album_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def get_listings(self, session: ScrapeSession, identifier: str, url: URL) -> List[MediaItem]:
        """Handles album scraping"""
        media_items = []
        try:
            content = await session.get_json(self.api / "list" / identifier)
            for file in content['files']:
                link = await self.create_download_link(file['id'])
                try:
                    filename, ext = await get_filename_and_ext(file['name'])
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue
                complete = await self.SQL_Helper.check_complete_singular("pixeldrain", link)
                media_item = MediaItem(link, url, complete, filename, ext, filename)
                media_items.append(media_item)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return media_items

    async def get_file_name(self, session: ScrapeSession, identifier: str) -> str:
        """Gets filename for the given file identifier"""
        content = await session.get_json(self.api / 'file' / identifier / 'info')
        return content['name']

    async def create_download_link(self, file: str) -> URL:
        """Gets download links for the file given"""
        return (self.api / 'file' / file).with_query('download')
