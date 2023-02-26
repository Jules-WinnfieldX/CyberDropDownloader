from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, get_filename_and_ext, \
    get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class LoveFapCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for lovefap scraping"""
        album_obj = AlbumItem("Loose LoveFap Files", [])

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
        if await check_direct(url):
            url_path = await get_db_path(url)
            complete = await self.SQL_Helper.check_complete_singular("lovefap", url_path)
            filename, ext = await get_filename_and_ext(url.name)
            media = MediaItem(url, url, complete, filename, ext, filename)
            await album_obj.add_media(media)
            await self.SQL_Helper.insert_album("lovefap", "", album_obj)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return album_obj

        try:
            if "video" in url.parts:
                await self.fetch_video(session, url, album_obj)
            else:
                await self.fetch_album(session, url, album_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return album_obj

        url_path = await get_db_path(url)
        await self.SQL_Helper.insert_album("cyberdrop", url_path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj

    async def fetch_album(self, session: ScrapeSession, url: URL, album_obj: AlbumItem):
        """Gets media_items for albums, and adds them to the Album_obj"""
        url_path = await get_db_path(url)
        soup = await session.get_BS4(url)

        title = soup.select_one('div[class=albums-content-header] span[style*="float: left"]').get_text()
        if title is None:
            title = url.name
        title = await make_title_safe(title)
        await album_obj.set_new_title(title)

        links = soup.select('div[class="file picture"] a')
        links.extend(soup.select('div[class="file picture"] a'))
        for link in links:
            link = link.get('href')
            if link.startswith('/'):
                link = url.host + link
            link = URL(link)
            if "video" in link.parts:
                await self.fetch_video(session, url, album_obj)
            else:
                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue

                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("lovefap", url_path)
                media = MediaItem(link, url, complete, filename, ext, filename)
                await album_obj.add_media(media)

    async def fetch_video(self, session: ScrapeSession, url: URL, album_obj: AlbumItem):
        """Gets media_items for video links"""
        soup = await session.get_BS4(url)
        video = soup.select_one("video[id=main-video] source")
        if video:
            link = URL(video.get("src"))
            try:
                filename, ext = await get_filename_and_ext(link.name)
            except NoExtensionFailure:
                logger.debug("Couldn't get extension for %s", str(link))
                return

            url_path = await get_db_path(link)
            complete = await self.SQL_Helper.check_complete_singular("lovefap", url_path)
            media = MediaItem(link, url, complete, filename, ext, filename)
            await album_obj.add_media(media)
