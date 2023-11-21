from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import field
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.clients.errors import FailedLoginFailure
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import log, get_download_path, remove_id, error_handling_wrapper

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class Crawler(ABC):
    def __init__(self, manager: Manager, domain: str, folder_domain: str):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.domain = domain
        self.folder_domain = folder_domain

        self.complete = False
        self.logged_in = field(init=False)

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

    async def startup(self) -> None:
        """Starts the crawler"""
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue(self.domain)
        self.download_queue = await self.manager.queue_manager.get_download_queue(self.domain)

        self.client = self.manager.client_manager.scraper_session

    async def finish_task(self) -> None:
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

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @abstractmethod
    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Director for scraping"""
        raise NotImplementedError("Must override in child class")

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        original_filename, filename = await remove_id(self.manager, filename, ext)

        check_complete = await self.manager.db_manager.history_table.check_complete(self.domain, url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, self.folder_domain)
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, original_filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def handle_external_links(self, scrape_item: ScrapeItem) -> None:
        """Maps external links to the scraper class"""
        await self.manager.queue_manager.url_objects_to_map.put(scrape_item)

    @error_handling_wrapper
    async def forum_login(self, login_url: URL, session_cookie: str, username: str, password: str, wait_time: int = 0) -> None:
        if session_cookie:
            self.client.client_manager.cookies.update_cookies({"xf_user": session_cookie},
                                                              response_url=URL("https://" + login_url.host))
        if (not username or not password) and not session_cookie:
            await log(f"Login wasn't provided for {login_url.host}")
            raise FailedLoginFailure(status=401, message="Login wasn't provided")
        attempt = 0

        while True:
            while True:
                try:
                    if attempt == 5:
                        raise FailedLoginFailure(status=403, message="Failed to login after 5 attempts")

                    assert login_url.host is not None

                    text = await self.client.get_text(self.domain, login_url)
                    if "You are already logged in" in text:
                        self.logged_in = True
                        return

                    await asyncio.sleep(wait_time)
                    soup = BeautifulSoup(text, 'html.parser')

                    inputs = soup.select('form input')
                    data = {
                        elem['name']: elem['value']
                        for elem in inputs
                        if elem.get('name') and elem.get('value')
                    }
                    data.update({
                        "login": username,
                        "password": password,
                        "_xfRedirect": str(URL("https://" + login_url.host))
                    })
                    await self.client.post_data(self.domain, login_url / "login", data=data, req_resp=False)
                    await asyncio.sleep(wait_time)
                    text = await self.client.get_text(self.domain, login_url)
                    if "You are already logged in" not in text:
                        continue

                    self.logged_in = True
                except asyncio.exceptions.TimeoutError:
                    attempt += 1
                    continue