from __future__ import annotations

import re
from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem
from cyberdrop_dl.utils.utilities import FILE_FORMATS, get_filename_and_ext, sanitize_folder, error_handling_wrapper

if TYPE_CHECKING:
    from asyncio import Queue
    from pathlib import Path
    from typing import Tuple

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem


class BunkrCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.primary_base_domain = URL("https://bunkrr.su")
        self._current_is_album: bool = field(init=False)

        self.complete = False
        self.unfinished_count = 0

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        download_limit = self.manager.config_manager.settings_data.get("max_simultaneous_downloads_per_domain")
        download_limit = 2 if download_limit > 2 else download_limit

        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("bunkr")
        self.download_queue = await self.manager.queue_manager.get_download_queue("bunkr", download_limit)

        self.client = await self.manager.client_manager.get_scraper_session("bunkr")

    async def run_loop(self) -> None:
        """Runs the crawler loop"""
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            if item.url in self.scraped_items:
                continue

            self.complete = False
            self.unfinished_count += 1

            self.scraped_items.append(item.url)
            self._current_is_album = False
            await self.fetch(item)

            self.scraper_queue.task_done()
            self.unfinished_count -= 1
            if self.unfinished_count == 0 and self.scraper_queue.empty():
                self.complete = True

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)
        scrape_item.url = await self.get_stream_link(scrape_item.url)

        if scrape_item.url.path.startswith("/a/"):
            self._current_is_album = True
            await self.album(self, scrape_item)
            return

        elif scrape_item.url.path.startswith("/v/"):
            await self.video(self, scrape_item)

        else:
            await self.other(self, scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
        for elem in title.find_all("span"):
            elem.decompose()
        title = await sanitize_folder(title.get_text())
        if scrape_item.parent_title:
            title = scrape_item.parent_title + " / " + title

        for file in soup.select('a[class*="grid-images_box-link"]'):
            link = file.get("href")
            if link.startswith("/"):
                link = URL("https://" + scrape_item.url.host + link)
            link = URL(link)
            link = await self.get_stream_link(link)
            await self.fetch(ScrapeItem(link, title))

    @error_handling_wrapper
    async def video(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a video"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        link_container = soup.select("a[class*=bg-blue-500]")[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item.url, scrape_item.parent_title, filename, ext)

    @error_handling_wrapper
    async def other(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an image/other file"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("bunkr", scrape_item.url)
        link_container = soup.select('a[class*="text-white inline-flex"]')[-1]
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)

        await self.handle_file(link, scrape_item.url, scrape_item.parent_title, filename, ext)

    async def handle_file(self, url: URL, referer: URL, folder_name: str, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await self.remove_id(filename, ext)

        check_complete = self.manager.db_manager.history_table.check_complete("bunkr", url)
        if check_complete:
            return

        download_folder = await self.get_download_path(folder_name)
        media_item = MediaItem(url, referer, download_folder, filename, ext, original_filename)
        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_download_path(self, folder_name) -> Path:
        """Returns the path to the download folder"""
        if self._current_is_album:
            return self.manager.config_manager.settings_data["download_folder"] / folder_name
        else:
            return self.manager.config_manager.settings_data["download_folder"] / folder_name / "Loose Bunkr Files"

    async def remove_id(self, filename: str, ext: str) -> Tuple[str, str]:
        """Removes the additional string bunkr adds to the end of every filename"""
        original_filename = filename
        if self.manager.config_manager.settings_data["remove_generated_id_from_filenames"]:
            original_filename = filename
            filename = filename.rsplit(ext, 1)[0]
            filename = filename.rsplit("-", 1)[0]
            if ext not in filename:
                filename = filename + ext
            return original_filename, filename

    async def get_stream_link(self, url: URL) -> URL:
        cdn_possibilities = r"^(?:(?:(?:media-files|cdn|c|pizza|cdn-burger)[0-9]{0,2})|(?:(?:big-taco-|cdn-pizza)[0-9]{0,2}(?:redir)?))\.bunkr?\.[a-z]{2,3}$"

        if not re.match(cdn_possibilities, url.host):
            return url

        ext = url.suffix.lower()
        if ext == "":
            return url

        if ext in FILE_FORMATS['Images']:
            url = url.with_host(re.sub(r"^cdn(\d*)\.", r"i\1.", url.host))
        elif ext in FILE_FORMATS['Videos']:
            url = self.primary_base_domain / "v" / url.parts[-1]
        else:
            url = self.primary_base_domain / "d" / url.parts[-1]

        return url
