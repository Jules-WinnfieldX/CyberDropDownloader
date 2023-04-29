from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import AlbumItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.data_classes import MediaItem
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class FapelloCrawler:
    def __init__(self, *, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> Optional[AlbumItem]:
        """Basic director for fapello"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        if not str(url).endswith("/"):
            url = url / ""

        album_obj = await self.parse_profile(session, url)

        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return album_obj

    async def parse_profile(self, session: ScrapeSession, url: URL) -> Optional[AlbumItem]:
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
                link = URL(post.get('href'))
                if link:
                    media_items = await self.parse_post(session, link)
                    for media in media_items:
                        await album_obj.add_media(media)

            next_page = soup.select_one('div[id="next_page"] a')
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    await album_obj.extend(await self.parse_profile(session, URL(next_page)))
            await self.SQL_Helper.insert_album("fapello", url, album_obj)
            return album_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)
            return None

    async def parse_post(self, session: ScrapeSession, url: URL) -> list[MediaItem]:
        """Parses posts, returns list of MediaItem"""
        results = []
        try:
            soup = await session.get_BS4(url)

            content_section = soup.select_one('div[class="flex justify-between items-center"]')

            images = content_section.select("img")
            for image in images:
                download_link = URL(image.get('src'))
                try:
                    media_item = await create_media_item(download_link, url, self.SQL_Helper, "fapello")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", download_link)
                    continue
                results.append(media_item)

            videos = content_section.select("source")
            for video in videos:
                download_link = URL(video.get('src'))
                try:
                    media_item = await create_media_item(download_link, url, self.SQL_Helper, "fapello")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", download_link)
                    continue
                results.append(media_item)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

        return results
