from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import (
    check_direct,
    create_media_item,
    log,
    logger,
    make_title_safe,
)
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class ShareXCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.limiter = AsyncLimiter(15, 1)

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director for ShareX scraper"""
        assert url.host is not None
        domain_obj = DomainItem(url.host.lower(), {})

        log(f"Starting: {url}", quiet=self.quiet, style="green")

        if await check_direct(url):
            url = url.with_name(url.name.replace('.md.', '.').replace('.th.', '.'))
            url = await self.jpg_fish_from_church(url)
            media_item = await create_media_item(url, url, self.SQL_Helper, "sharex")
            await domain_obj.add_media("Loose ShareX Files", media_item)
        elif "album" in url.parts or "a" in url.parts:
            await self.parse(session=session, url=url, domain_obj=domain_obj)
        elif "albums" in url.parts:
            await self.get_albums(session, url, domain_obj)
        elif 'image' in url.parts or 'img' in url.parts or 'images' in url.parts:
            await self.get_singular(session, url, domain_obj)
        else:
            await self.parse_profile(session, url, domain_obj)

        await self.SQL_Helper.insert_domain("sharex", url, domain_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return domain_obj

    async def jpg_fish_from_church(self, url: URL) -> URL:
        pattern2 = r"simp([1-5])\.jpg\.church/"
        return URL(re.sub(pattern2, r'simp\1.jpg.fish/', str(url)))

    async def get_albums(self, session: ScrapeSession, url: URL, domain_obj: DomainItem) -> None:
        """Handles scraping for Albums"""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            albums = soup.select("a[class='image-container --media']")
            for album in albums:
                album_url = URL(album.get('href'))
                await self.parse(session=session, url=album_url, domain_obj=domain_obj)

            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    await self.get_albums(session, next_page, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_singular(self, session: ScrapeSession, url: URL, domain_obj: DomainItem) -> None:
        """Handles scraping for singular files"""
        await asyncio.sleep(1)
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            link = URL(soup.select_one("input[id=embed-code-2]").get('value'))
            link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
            link = await self.jpg_fish_from_church(link)

            media_item = await create_media_item(link, url, self.SQL_Helper, "sharex")
            await domain_obj.add_media("Loose ShareX Files", media_item)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_sub_album_links(self, session: ScrapeSession, url: URL, og_title: str,
                                  domain_obj: DomainItem) -> None:
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            albums = soup.select("div[class=pad-content-listing] div")
            for album in albums:
                album_url = album.get('data-url-short')
                if album_url is not None:
                    album_url = URL(album_url)
                    await self.parse(session=session, url=album_url, og_title=og_title, domain_obj=domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def parse_profile(self, session: ScrapeSession, url: URL, domain_obj: DomainItem) -> None:
        """Handles scraping for profiles"""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            title = soup.select_one("div[class=header] h1 strong").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())
            await self.get_list_links(session, url, title, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def get_list_links(self, session: ScrapeSession, url: URL, title: str, domain_obj: DomainItem) -> None:
        """Gets final links and adds to domain_obj"""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            assert url.host is not None
            if 'jpg.fish' in url.host or 'jpg.church' in url.host:
                links = soup.select("a[href*=img] img")
            else:
                links = soup.select("a[href*=image] img")
            for link in links:
                link = URL(link.get('src'))
                link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
                link = await self.jpg_fish_from_church(link)

                try:
                    media_item = await create_media_item(link, url, self.SQL_Helper, "sharex")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue
                await domain_obj.add_media(title, media_item)

            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    await self.get_list_links(session, next_page, title, domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)

    async def parse(self, *, session: ScrapeSession, url: URL, og_title=None, domain_obj: DomainItem) -> None:
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)

            title = soup.select_one("a[data-text=album-name]").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())

            if og_title is not None:
                title = og_title + "/" + title

            try:
                sub_albums = URL(soup.select_one("a[id=tab-sub-link]").get("href"))
                await self.get_sub_album_links(session, sub_albums, title, domain_obj)
            finally:
                list_recent = URL(soup.select_one("a[id=list-most-recent-link]").get("href"))
                await self.get_list_links(session, list_recent, title, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            log(f"Error: {url}", quiet=self.quiet, style="red")
            logger.debug(e)
