from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from ..base_functions.base_functions import (
    FILE_FORMATS,
    get_filename_and_ext,
    log,
    logger,
    make_title_safe,
)
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class BunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, remove_bunkr_id: bool, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.remove_bunkr_id = remove_bunkr_id
        self.limiter = AsyncLimiter(3, 1)

        self.error_writer = error_writer

        self.primary_base_domain = URL("https://bunkrr.su")
        self.api_link = URL(f"https://api-v2.{self.primary_base_domain.host}")

    async def fetch(self, session: ScrapeSession, url: URL) -> AlbumItem:
        """Scraper for Bunkr"""
        album_obj = AlbumItem("Loose Bunkr Files", [])
        log(f"Starting: {url}", quiet=self.quiet, style="green")

        url = await self.get_stream_link(url)

        if "a" in url.parts:
            album_obj = await self.get_album(session, url)
            await self.SQL_Helper.insert_album("bunkr", url, album_obj)

            if album_obj.media:
                log(f"Finished: {url}", quiet=self.quiet, style="green")
            return album_obj

        elif "v" in url.parts:
            media = await self.get_video(session, url)
        else:
            media = await self.get_other(session, url)
        if not media.filename:
            return album_obj
        await album_obj.add_media(media)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        if not media.complete:
            await self.SQL_Helper.insert_media("bunkr", "", media)
        return album_obj

    async def get_stream_link(self, url: URL):
        cdn_possibilities = r"^(?:(?:(?:media-files|cdn|c|pizza|cdn-burger)[0-9]{0,2})|(?:(?:big-taco-|cdn-pizza|cdn-meatballs|cdn-milkshake)[0-9]{0,2}(?:redir)?))\.bunkr?\.[a-z]{2,3}$"

        if not re.match(cdn_possibilities, url.host):
            return url

        ext = url.suffix.lower()
        if ext == "":
            return url

        if ext in FILE_FORMATS['Images']:
            url = self.primary_base_domain / "i" / url.parts[-1]
        elif ext in FILE_FORMATS['Videos']:
            url = self.primary_base_domain / "v" / url.parts[-1]
        else:
            url = self.primary_base_domain / "d" / url.parts[-1]

        return url

    async def remove_id(self, filename: str, ext: str):
        """Removes the additional string bunkr adds to the end of every filename"""
        original_filename = filename
        if self.remove_bunkr_id:
            filename = filename.rsplit(ext, 1)[0]
            filename = filename.rsplit("-", 1)[0]
            if ext not in filename:
                filename = filename + ext
        return original_filename, filename

    async def get_video(self, session: ScrapeSession, url: URL):
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
                link = soup.select("a[class*=bg-blue-500]")
                link = link[-1]
                link_resp = URL(link.get("href"))

            try:
                filename, ext = await get_filename_and_ext(link_resp.name)
            except NoExtensionFailure:
                filename, ext = await get_filename_and_ext(url.name)

            original_filename, filename = await self.remove_id(filename, ext)

            await self.SQL_Helper.fix_bunkr_entries(link_resp, original_filename)
            complete = await self.SQL_Helper.check_complete_singular("bunkr", link_resp)
            return MediaItem(link_resp, url, complete, filename, ext, original_filename)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            logger.debug(e)
            return MediaItem(url, url, False, "", "", "")

    async def get_other(self, session: ScrapeSession, url: URL):
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
                link = soup.select('a[class*="text-white inline-flex"]')
                link = link[-1]
                link_resp = URL(link.get("href"))

            try:
                filename, ext = await get_filename_and_ext(link_resp.name)
            except NoExtensionFailure:
                filename, ext = await get_filename_and_ext(url.name)

            original_filename, filename = await self.remove_id(filename, ext)

            await self.SQL_Helper.fix_bunkr_entries(link_resp, original_filename)
            complete = await self.SQL_Helper.check_complete_singular("bunkr", link_resp)
            return MediaItem(link_resp, url, complete, filename, ext, original_filename)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            logger.debug(e)
            return MediaItem(url, url, False, "", "", "")

    async def get_album(self, session: ScrapeSession, url: URL):
        """Iterates through an album and creates the media items"""

        url = self.primary_base_domain.with_path(url.path)

        album = AlbumItem(url.name, [])
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
            for elem in title.find_all("span"):
                elem.decompose()
            title = await make_title_safe(title.get_text())
            await album.set_new_title(title)
            for file in soup.select('a[class*="grid-images_box-link"]'):
                link = file.get("href")

                assert url.host is not None
                if link.startswith("/"):
                    link = URL("https://" + url.host + link)
                link = URL(link)

                try:
                    referer = await self.get_stream_link(link)
                except Exception as e:
                    logger.debug("Error encountered while handling %s", link, exc_info=True)
                    await self.error_writer.write_errored_scrape(link, e, self.quiet)
                    logger.debug(e)
                    continue

                if "v" in referer.parts:
                    media = await self.get_video(session, referer)
                else:
                    media = await self.get_other(session, referer)
                if not media.filename:
                    continue
                await album.add_media(media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return album
