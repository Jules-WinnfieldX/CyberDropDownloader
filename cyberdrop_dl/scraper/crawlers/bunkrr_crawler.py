from __future__ import annotations

import calendar
import datetime
import re
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import FILE_FORMATS, get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class BunkrrCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "bunkrr", "Bunkrr")
        self.primary_base_domain = URL("https://bunkr.sk")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)
        scrape_item.url = await self.get_stream_link(scrape_item.url)

        if scrape_item.url.host.startswith("get"):
            scrape_item.url = await self.reinforced_link(scrape_item.url)
            if not scrape_item.url:
                return
            scrape_item.url = await self.get_stream_link(scrape_item.url)

        if "a" in scrape_item.url.parts:
            await self.album(scrape_item)
        elif "v" in scrape_item.url.parts:
            await self.video(scrape_item)
        else:
            await self.other(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        scrape_item.url = self.primary_base_domain.with_path(scrape_item.url.path)
        album_id = scrape_item.url.parts[2]
        results = await self.get_album_results(album_id)

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)
        title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
        for elem in title.find_all("span"):
            elem.decompose()

        title = await self.create_title(title.get_text().strip(), scrape_item.url.parts[2], None)
        await scrape_item.add_to_parent_title(title)

        card_listings = soup.select('div[class*="grid-images_box rounded-lg"]')
        for card_listing in card_listings:
            file = card_listing.select_one('a[class*="grid-images_box-link"]')
            date = await self.parse_datetime(card_listing.select_one('p[class*="date"]').text)
            link = file.get("href")
            if link.startswith("/"):
                link = URL("https://" + scrape_item.url.host + link)
            link = URL(link)
            link = await self.get_stream_link(link)

            try:
                filename = card_listing.select_one("div[class*=details]").select_one("p").text
                file_ext = "." + filename.split(".")[-1]
                if file_ext.lower() not in FILE_FORMATS['Images'] and file_ext.lower() not in FILE_FORMATS['Videos']:
                    raise FileNotFoundError()
                image_obj = file.select_one("img")
                src = image_obj.get("src")
                src = src.replace("/thumbs/", "/")
                src = URL(src, encoded=True)
                src = src.with_suffix(file_ext)
                src = src.with_query("download=true")
                if file_ext.lower() not in FILE_FORMATS['Images']:
                    src = src.with_host(src.host.replace("i-", ""))
                new_scrape_item = await self.create_scrape_item(scrape_item, link, "", True, album_id, date)

                if "no-image" in src.name:
                    raise FileNotFoundError("No image found, reverting to parent")

                filename, ext = await get_filename_and_ext(src.name)
                if not await self.check_album_results(src, results):
                    await self.handle_file(src, new_scrape_item, filename, ext)
            except FileNotFoundError:
                self.manager.task_group.create_task(self.run(ScrapeItem(link, scrape_item.parent_title, True, album_id, date)))

    @error_handling_wrapper
    async def video(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a video"""
        scrape_item.url = self.primary_base_domain.with_path(scrape_item.url.path)
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)
        link_container = soup.select("a[class*=bg-blue-500]")[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            try:
                link_container = soup.select_one("source")
                link = URL(link_container.get('src'))
                filename, ext = await get_filename_and_ext(link.name)
            except NoExtensionFailure:
                if "get" in link.host:
                    link = await self.reinforced_link(link)
                    if not link:
                        return
                    filename, ext = await get_filename_and_ext(link.name)
                else:
                    filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def other(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image/other file"""
        scrape_item.url = self.primary_base_domain.with_path(scrape_item.url.path)
        
        if await self.check_complete_from_referer(scrape_item):
            return

        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)
        link_container = soup.select('a[class*="text-white inline-flex"]')[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            if "get" in link.host:
                link = await self.reinforced_link(link)
                if not link:
                    return
                filename, ext = await get_filename_and_ext(link.name)
            else:
                filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item, filename, ext)

    @error_handling_wrapper
    async def reinforced_link(self, url: URL) -> URL:
        """Gets the download link for a given reinforced URL"""
        """get.bunkr.su"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, url)
        
        try:
            link_container = soup.select('a[download*=""]')[-1]
        except IndexError:
            link_container = soup.select('a[class*=download]')[-1]
        link = URL(link_container.get('href'))
        return link

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_stream_link(self, url: URL) -> URL:
        """Gets the stream link for a given url"""
        cdn_possibilities = r"^(?:(?:(?:media-files|cdn|c|pizza|cdn-burger|cdn-nugget|burger|taquito|pizza|fries|meatballs|milkshake|kebab)[0-9]{0,2})|(?:(?:big-taco-|cdn-pizza|cdn-meatballs|cdn-milkshake|i.kebab|i.fries|i-nugget|i-milkshake)[0-9]{0,2}(?:redir)?))\.bunkr?\.[a-z]{2,3}$"

        if not re.match(cdn_possibilities, url.host):
            return url

        ext = url.suffix.lower()
        if ext == "":
            return url

        if ext in FILE_FORMATS['Images']:
            url = self.primary_base_domain / "d" / url.parts[-1]
        elif ext in FILE_FORMATS['Videos']:
            url = self.primary_base_domain / "v" / url.parts[-1]
        else:
            url = self.primary_base_domain / "d" / url.parts[-1]

        return url

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%H:%M:%S %d/%m/%Y")
        return calendar.timegm(date.timetuple())
