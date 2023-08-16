from __future__ import annotations

import html
import re
from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem
from cyberdrop_dl.utils.utilities import FILE_FORMATS, get_filename_and_ext, sanitize_folder

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem


class BunkrCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.client: ScraperClient = field(init=False)

        self.primary_base_domain = URL("https://bunkrr.su")
        self._current_is_album: bool = field(init=False)

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self):
        download_limit = self.manager.config_manager.settings_data.get("max_simultaneous_downloads_per_domain")
        download_limit = 2 if download_limit > 2 else download_limit

        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("bunkr")
        self.download_queue = await self.manager.queue_manager.get_download_queue("bunkr", download_limit)

        self.client = await self.manager.client_manager.get_scraper_session("bunkr")

    async def run_loop(self):
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            if item.url in self.scraped_items:
                continue
            self.scraped_items.append(item.url)
            self._current_is_album = False
            await self.fetch(item)
            self.scraper_queue.task_done()

    async def fetch(self, scrape_item: ScrapeItem):
        """Determines where to send the scrape item based on the url"""
        url = scrape_item.url
        extension = ('.' + url.parts[-1].split('.')[-1]).lower()

        if url.path.startswith("/a/"):
            self._current_is_album = True
            await self.album(scrape_item)
            return

        elif url.path.startswith("/v/") or extension in FILE_FORMATS['Videos']:
            await self.video(scrape_item)

        elif url.host.startswith("i") or extension in FILE_FORMATS['Images']:
            await self.image(scrape_item)

        elif (url.path.startswith("/d/") or
              (extension not in FILE_FORMATS['Images'] and extension not in FILE_FORMATS['Videos'])):
            await self.other(scrape_item)

    async def album(self, scrape_item: ScrapeItem):
        """Scrapes an album"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(scrape_item.url)
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

    async def video(self, scrape_item: ScrapeItem):
        """Scrapes a video"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(scrape_item.url)
        link_container = soup.select_one("a[class*=bg-blue-500]")
        link = URL(link_container.get('href'))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
        if ext not in FILE_FORMATS['Images']:
            link = await self.check_for_la(link)

        await self.handle_file(link, scrape_item.url, scrape_item.parent_title, filename, ext)

    async def image(self, scrape_item: ScrapeItem):
        """Scrapes an image"""
        link = await self.get_stream_link(scrape_item.url)
        scrape_item.url = link

        filename, ext = await get_filename_and_ext(link.name)
        original_filename, filename = await self.remove_id(filename, ext)
        await self.handle_file(link, scrape_item.url, scrape_item.parent_title, filename, ext)

    async def other(self, scrape_item: ScrapeItem):
        """Scrapes an "other" file"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(scrape_item.url)
        head = soup.select_one("head")
        scripts = head.select('script[type="text/javascript"]')
        link = None

        for script in scripts:
            if script.text and "link.href" in script.text:
                link = script.text.split('link.href = "')[-1].split('";')[0]
                break
        if not link:
            raise

        # URL Cleanup
        link = URL(html.unescape(str(link)))

        try:
            filename, ext = await get_filename_and_ext(link.name)
        except NoExtensionFailure:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
        if ext not in FILE_FORMATS['Images']:
            link = await self.check_for_la(link)

        await self.handle_file(link, scrape_item.url, scrape_item.parent_title, filename, ext)

    async def handle_file(self, url: URL, referer: URL, folder_name: str, filename: str, ext: str):
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await self.remove_id(filename, ext)

        check_complete = self.manager.db_manager.history_table.check_complete("bunkr", url)
        if check_complete:
            return

        download_folder = await self.get_download_path(folder_name)
        media_item = MediaItem(url, referer, download_folder, filename, ext, original_filename)
        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_download_path(self, folder_name):
        """Returns the path to the download folder"""
        if self._current_is_album:
            return self.manager.config_manager.settings_data["download_folder"] / folder_name
        else:
            return self.manager.config_manager.settings_data["download_folder"] / folder_name / "Loose Bunkr Files"

    async def remove_id(self, filename: str, ext: str):
        """Removes the additional string bunkr adds to the end of every filename"""
        original_filename = filename
        if self.manager.config_manager.settings_data["remove_generated_id_from_filenames"]:
            original_filename = filename
            filename = filename.rsplit(ext, 1)[0]
            filename = filename.rsplit("-", 1)[0]
            if ext not in filename:
                filename = filename + ext
            return original_filename, filename

    async def check_for_la(self, url: URL):
        assert url.host is not None
        if "12" in url.host:
            url_host = url.host.replace(".su", ".la").replace(".ru", ".la")
            url = url.with_host(url_host)
        return url

    async def get_stream_link(self, url: URL):
        cdn_possibilities = r"^(?:media-files|cdn|c)[0-9]{0,2}\.bunkrr?\.[a-z]{2,3}$"

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
