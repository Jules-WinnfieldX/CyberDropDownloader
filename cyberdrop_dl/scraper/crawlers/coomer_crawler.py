from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log, get_download_path

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class CoomerCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.complete = False

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(10, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("coomer")
        self.download_queue = await self.manager.queue_manager.get_download_queue("coomer")

        self.client = self.manager.client_manager.scraper_session

    async def finish_task(self):
        self.scraper_queue.task_done()
        if self.scraper_queue.empty():
            self.complete = True

    async def run_loop(self) -> None:
        """Runs the crawler loop"""
        while True:
            item: ScrapeItem = await self.scraper_queue.get()
            await log(f"Scrape Starting: {item.url}")
            if item.url in self.scraped_items:
                await self.finish_task()
                continue

            self.complete = False
            self.scraped_items.append(item.url)
            await self.fetch(item)

            await log(f"Scrape Finished: {item.url}")
            await self.finish_task()

    async def fetch(self, scrape_item: ScrapeItem):
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "thumbnails" in scrape_item.url.parts:
            parts = [x for x in scrape_item.url.parts if x not in ("thumbnail", "/")]
            link = URL(f"https://{scrape_item.url.host}/{'/'.join(parts)}")
            scrape_item.url = link
            await self.handle_direct_link(scrape_item)
        elif "data" in scrape_item.url.parts:
            await self.handle_direct_link(scrape_item)
        elif "post" in scrape_item.url.parts:
            await self.post(scrape_item)
        else:
            await self.profile(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def profile(self, scrape_item: ScrapeItem):
        """Scrapes a profile"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("coomer", scrape_item.url)

        posts = soup.select("article[class*=post-card] a")
        for post in posts:
            path = post.get("href")
            if path:
                link = URL(f"https://{scrape_item.url.host}{path}")
                await self.scraper_queue.put(ScrapeItem(link, scrape_item.parent_title))

        next_page = soup.select_one("a[class*=next]")
        if next_page:
            next_page = next_page.get('href')
            if next_page:
                link = URL(f"https://{scrape_item.url.host}{next_page}")
                await self.scraper_queue.put(ScrapeItem(link, scrape_item.parent_title))

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem):
        """Scrapes a post"""
        soup = await self.manager.db_manager.cache_table.get_blob(scrape_item.url)
        if not soup:
            async with self.request_limiter:
                soup = await self.client.get_BS4("coomer", scrape_item.url)
            await self.manager.db_manager.cache_table.insert_blob(str(soup), scrape_item.url)
        else:
            soup = BeautifulSoup(soup, "html.parser")

        user = soup.select_one("meta[name=user]").get("content")
        time = soup.select_one("meta[name=published]").get("content")
        title = soup.select_one("h1[class=post__title]").get_text().replace('\n', '').replace("..", "")
        post_id = soup.select_one("meta[name=id]").get("content")

        text_block = soup.select_one('div[class=post__content]')
        if text_block:
            if "#AD" in text_block.text and self.manager.config_manager.settings_data['Ignore_Options']['ignore_coomer_ads']:
                return

        await scrape_item.add_to_parent_title(user + f" ({scrape_item.url.host})")
        if self.manager.config_manager.settings_data['Download_Options']['separate_posts']:
            post_title = f"{time} - {title}"
            if self.manager.config_manager.settings_data['Download_Options']['include_album_id_in_folder_name']:
                post_title = post_id + " - " + post_title
            await scrape_item.add_to_parent_title(post_title)

        images = soup.select('a[class="fileThumb"]')
        for image in images:
            await self.scraper_queue.put(ScrapeItem(URL(image.get("href")), scrape_item.parent_title, True))

        downloads = soup.select('a[class=post__attachment-link]')
        for download in downloads:
            await self.scraper_queue.put(ScrapeItem(URL(download.get("href")), scrape_item.parent_title, True))

    @error_handling_wrapper
    async def handle_direct_link(self, scrape_item: ScrapeItem) -> None:
        """Handles a direct link"""
        filename, ext = await get_filename_and_ext(scrape_item.url.query["f"])
        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        check_complete = await self.manager.db_manager.history_table.check_complete("coomer", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "Coomer")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, filename)
        await self.download_queue.put(media_item)
