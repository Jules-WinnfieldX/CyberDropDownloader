from yarl import URL

from ..base_functions.base_functions import log, logger, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class PixelDrainCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.api = URL('https://pixeldrain.com/api/')

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for pixeldrain scraping"""
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
        album_obj = AlbumItem("Loose Pixeldrain Files", [])

        identifier = str(url).split('/')[-1]
        if url.parts[1] == 'l':
            await album_obj.set_new_title(url.name)
            media_items = await self.get_listings(session, identifier, url)
            if media_items:
                for media_item in media_items:
                    await album_obj.add_media(media_item)
        else:
            link = await self.create_download_link(identifier)
            url_path = await get_db_path(link)
            complete = await self.SQL_Helper.check_complete_singular("anonfiles", url_path)
            filename, ext = await get_filename_and_ext(await self.get_file_name(session, identifier))
            media_item = MediaItem(link, url, complete, filename, ext)
            await album_obj.add_media(media_item)

        await self.SQL_Helper.insert_album("pixeldrain", url.path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj

    async def get_listings(self, session: ScrapeSession, identifier: str, url: URL):
        """Handles album scraping"""
        media_items = []
        try:
            content = await session.get_json((self.api / "list" / identifier))
            for file in content['files']:
                link = await self.create_download_link(file['id'])
                try:
                    filename, ext = await get_filename_and_ext(file['name'])
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue
                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("pixeldrain", url_path)
                media_item = MediaItem(link, url, complete, filename, ext)
                media_items.append(media_item)
            return media_items

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_file_name(self, session: ScrapeSession, identifier: str):
        """Gets filename for the given file identifier"""
        content = await session.get_json((self.api / 'file' / identifier / 'info'))
        filename = content['name']
        return filename

    async def create_download_link(self, file: str):
        """Gets download links for the file given"""
        final_url = (self.api / 'file' / file).with_query('download')
        return final_url
