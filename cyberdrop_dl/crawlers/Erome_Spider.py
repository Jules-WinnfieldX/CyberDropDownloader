from __future__ import annotations

from typing import TYPE_CHECKING

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class EromeCrawler:
    def __init__(self, *, include_id: bool, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.include_id = include_id
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director function for Erome scraping"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        if 'a' in url.parts:
            domain_obj = await self.handle_album(session, url)
        else:
            domain_obj = await self.handle_profile(session, url)

        log(f"Finished: {url}", quiet=self.quiet, style="green")

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
                    media = await create_media_item(link, url, self.SQL_Helper, "erome")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", url)
                    continue
                await domain_obj.add_media(title, media)

            # Videos
            for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                link = URL(link['src'])
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "erome")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue
                await domain_obj.add_media(title, media)

            await self.SQL_Helper.insert_domain("erome", url, domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return domain_obj

    async def handle_profile(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Handler for erome profiles, sends albums to handle_album"""
        domain_obj = DomainItem("erome", {})
        try:
            soup = await session.get_BS4(url)
            title = url.name
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            for album in soup.select("a[class=album-link]"):
                album_url = URL(album.get('href'))
                await domain_obj.extend(await self.handle_album(session, album_url))
            await domain_obj.append_title(title)

            next_page = soup.select_one('a[rel="next"]')
            if next_page:
                next_page = next_page.get("href").split("page=")[-1]
                next_page = url.with_query(f"page={next_page}")
                await domain_obj.extend(await self.handle_profile(session, next_page))

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return domain_obj
