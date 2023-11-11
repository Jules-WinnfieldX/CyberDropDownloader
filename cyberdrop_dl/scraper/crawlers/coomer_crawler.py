from __future__ import annotations

from dataclasses import field
from typing import TYPE_CHECKING, Tuple, Dict

from aiolimiter import AsyncLimiter
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

        self.primary_base_domain = URL("https://coomer.su")
        self.api_url = URL("https://coomer.su/api/v1")

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
        elif "post" in scrape_item.url.parts:
            await self.post(scrape_item)
        elif "onlyfans" in scrape_item.url.parts or "fansly" in scrape_item.url.parts:
            await self.profile(scrape_item)
        else:
            await self.handle_direct_link(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def profile(self, scrape_item: ScrapeItem):
        """Scrapes a profile"""
        offset = 0
        service, user = await self.get_service_and_user(scrape_item)
        api_call = self.api_url / service / "user" / user
        while True:
            async with self.request_limiter:
                JSON_Resp = await self.client.get_json("coomer", api_call.with_query({"o": offset}))
                offset += 50
                if not JSON_Resp:
                    break

            for post in JSON_Resp:
                await self.handle_post_content(post, scrape_item, user)

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem):
        """Scrapes a post"""
        service, user, post_id = await self.get_service_user_and_post(scrape_item)
        api_call = self.api_url / service / "user" / user / "post" / post_id
        async with self.request_limiter:
            post = await self.client.get_json("coomer", api_call)
        await self.handle_post_content(post, scrape_item, user)

    @error_handling_wrapper
    async def handle_post_content(self, post: Dict, scrape_item: ScrapeItem, user: str):
        if "#ad" in post['content'] and self.manager.config_manager.settings_data['Ignore_Options']['ignore_coomer_ads']:
            return

        date = post["published"].replace("T", " ")
        post_id = post["id"]
        post_title = post["title"]

        async def handle_file(file_obj):
            link = self.primary_base_domain / ("data" + file_obj['path'])
            link = link.with_query({"f": file_obj['name']})
            await self.create_new_scrape_item(link, scrape_item, user, post_title, post_id, date)

        if post['file']:
            await handle_file(post['file'])

        for file in post['attachments']:
            await handle_file(file)

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
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_service_and_user(self, scrape_item: ScrapeItem) -> Tuple[str, str]:
        user = scrape_item.url.parts[3]
        service = scrape_item.url.parts[1]
        return service, user

    async def get_service_user_and_post(self, scrape_item: ScrapeItem) -> Tuple[str, str, str]:
        user = scrape_item.url.parts[3]
        service = scrape_item.url.parts[1]
        post = scrape_item.url.parts[5]
        return service, user, post

    async def create_new_scrape_item(self, link: URL, old_scrape_item: ScrapeItem, user: str, title: str, post_id: str,
                                     date: str) -> None:
        post_title = None
        if self.manager.config_manager.settings_data['Download_Options']['separate_posts']:
            post_title = f"{date} - {title}"
            if self.manager.config_manager.settings_data['Download_Options']['include_album_id_in_folder_name']:
                post_title = post_id + " - " + post_title

        new_scrape_item = ScrapeItem(link, old_scrape_item.parent_title, True, possible_datetime=date)
        await new_scrape_item.add_to_parent_title(f"{user} ({old_scrape_item.url.host})")
        await new_scrape_item.add_to_parent_title(post_title)
        await self.scraper_queue.put(new_scrape_item)
