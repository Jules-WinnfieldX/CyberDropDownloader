from yarl import URL

from ..base_functions.base_functions import get_filename_and_ext, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class EromeCrawler:
    def __init__(self, *, include_id: bool, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director function for Erome scraping"""
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")

        if 'a' in url.parts:
            domain_obj = await self.handle_album(session, url)
        else:
            domain_obj = await self.handle_profile(session, url)

        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")

        return domain_obj

    async def handle_album(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Handler function for erome albums, adds media items to the domain item"""
        domain_obj = DomainItem("erome", {})
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one('div[class="col-sm-12 page-content"] h1').get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            # Images
            for link in soup.select('img[class="img-front lasyload"]'):
                link = URL(link['data-src'])
                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(url))
                    continue
                complete = await self.SQL_Helper.check_complete_singular("erome", link)
                media = MediaItem(link, url, complete, filename, ext, filename)
                await domain_obj.add_media(title, media)

            # Videos
            for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                link = URL(link['src'])
                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue
                complete = await self.SQL_Helper.check_complete_singular("erome", link)
                media = MediaItem(link, url, complete, filename, ext, filename)
                await domain_obj.add_media(title, media)

            await self.SQL_Helper.insert_domain("erome", url, domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        return domain_obj

    async def handle_profile(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Handler for erome profiles, sends albums to handle_album"""
        domain_obj = DomainItem("erome", {})
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one('h1[class="username"]').get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            for album in soup.select("a[class=album-link]"):
                url = URL(album.get('href'))
                await domain_obj.extend(await self.handle_album(session, url))
            await domain_obj.append_title(title)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        return domain_obj
