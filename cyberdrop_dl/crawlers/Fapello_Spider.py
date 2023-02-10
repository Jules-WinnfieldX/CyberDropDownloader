from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class FapelloCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Basic director for fapello"""
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        album_obj = await self.parse_profile(session, url)

        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        if not album_obj:
            return None
        return album_obj

    async def parse_profile(self, session: ScrapeSession, url: URL):
        """Profile parser, passes posts to parse_post"""
        try:
            soup, returned_url = await session.get_BS4_and_url(url)
            title = soup.select_one('h2[class="font-semibold lg:text-2xl text-lg mb-2 mt-4"]').get_text()
            title = title + " (Fapello)"
            title = await make_title_safe(title)

            album_obj = AlbumItem(title, [])

            # Fapello does circular looped paging
            if returned_url != url:
                return album_obj

            content_section = soup.select_one("div[id=content]")
            posts = content_section.select("a")
            for post in posts:
                link = post.get('href')
                if link:
                    media_items = await self.parse_post(session, link)
                    for media in media_items:
                        await album_obj.add_media(media)

            next_page = soup.select_one('div[id="next_page"] a')
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    await album_obj.extend(await self.parse_profile(session, URL(next_page)))
            await self.SQL_Helper.insert_album("fapello", url.path, album_obj)
            return album_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return

    async def parse_post(self, session: ScrapeSession, url: URL):
        """Parses posts, returns list of media_items"""
        try:
            soup = await session.get_BS4(url)
            results = []

            content_section = soup.select_one('div[class="flex justify-between items-center"]')

            images = content_section.select("img")
            for image in images:
                download_link = URL(image.get('src'))
                try:
                    filename, ext = await get_filename_and_ext(download_link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(download_link))
                    continue
                url_path = await get_db_path(download_link)
                complete = await self.SQL_Helper.check_complete_singular("fapello", url_path)
                results.append(MediaItem(download_link, url, complete, filename, ext))

            videos = content_section.select("source")
            for video in videos:
                download_link = URL(video.get('src'))
                try:
                    filename, ext = await get_filename_and_ext(download_link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(download_link))
                    continue
                url_path = await get_db_path(download_link)
                complete = await self.SQL_Helper.check_complete_singular("fapello", url_path)
                results.append(MediaItem(download_link, url, complete, filename, ext))

            return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return
