from __future__ import annotations

import asyncio
import copy
from abc import ABC, abstractmethod
from dataclasses import field
from typing import TYPE_CHECKING, Optional, Union, Any

from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.clients.errors import FailedLoginFailure
from cyberdrop_dl.downloader.downloader import Downloader
from cyberdrop_dl.utils.database.tables.history_table import get_db_path
from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem
from cyberdrop_dl.utils.utilities import log, get_download_path, remove_id, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class Crawler(ABC):
    def __init__(self, manager: Manager, domain: str, folder_domain: str):
        self.manager = manager
        self.downloader = field(init=False)
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)
        self._lock = asyncio.Lock()

        self.domain = domain
        self.folder_domain = folder_domain

        self.logged_in = field(init=False)

        self.scraped_items: list = []
        self.waiting_items = 0

    async def startup(self) -> None:
        """Starts the crawler"""
        self.client = self.manager.client_manager.scraper_session
        self.downloader = Downloader(self.manager, self.domain)
        await self.downloader.startup()

    async def run(self, item: ScrapeItem) -> None:
        """Runs the crawler loop"""
        if not item.url.host:
            return

        self.waiting_items += 1
        await self._lock.acquire()
        self.waiting_items -= 1
        if item.url.path_qs not in self.scraped_items:
            await log(f"Scrape Starting: {item.url}", 20)
            self.scraped_items.append(item.url.path_qs)
            await self.fetch(item)
            await log(f"Scrape Finished: {item.url}", 20)
        else:
            await log(f"Skipping {item.url} as it has already been scraped", 10)
        self._lock.release()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @abstractmethod
    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Director for scraping"""
        raise NotImplementedError("Must override in child class")

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the downloader"""
        if self.domain in ['cyberdrop', 'bunkrr']:
            original_filename, filename = await remove_id(self.manager, filename, ext)
        else:
            original_filename = filename

        download_folder = await get_download_path(self.manager, scrape_item, self.folder_domain)
        media_item = MediaItem(url, scrape_item.url, scrape_item.album_id, download_folder, filename, ext, original_filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        check_complete = await self.manager.db_manager.history_table.check_complete(self.domain, url, scrape_item.url)
        if check_complete:
            if media_item.album_id:
                await self.manager.db_manager.history_table.set_album_id(self.domain, media_item)
            await log(f"Skipping {url} as it has already been downloaded", 10)
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        if await self.manager.download_manager.get_download_limit(self.domain) == 1:
            await self.downloader.run(media_item)
        else:
            self.manager.task_group.create_task(self.downloader.run(media_item))

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_post_number(self, post_number: int, current_post_number: int) -> (bool, bool):
        """Checks if the program should scrape the current post"""
        """Returns (scrape_post, continue_scraping)"""
        scrape_single_forum_post = self.manager.config_manager.settings_data['Download_Options']['scrape_single_forum_post']

        if scrape_single_forum_post:
            if not post_number:
                return True, False
            if post_number == current_post_number:
                return True, False
            return False, True

        elif post_number:
            if post_number > current_post_number:
                return False, True

        return True, True

    async def handle_external_links(self, scrape_item: ScrapeItem) -> None:
        """Maps external links to the scraper class"""
        self.manager.task_group.create_task(self.manager.scrape_mapper.map_url(scrape_item))

    @error_handling_wrapper
    async def forum_login(self, login_url: URL, session_cookie: str, username: str, password: str, wait_time: int = 0) -> None:
        """Logs into a forum"""
        if session_cookie:
            self.client.client_manager.cookies.update_cookies({"xf_user": session_cookie},
                                                              response_url=URL("https://" + login_url.host))
        if (not username or not password) and not session_cookie:
            await log(f"Login wasn't provided for {login_url.host}", 30)
            raise FailedLoginFailure(status=401, message="Login wasn't provided")
        attempt = 0

        while True:
            try:
                attempt += 1
                if attempt == 5:
                    raise FailedLoginFailure(status=403, message="Failed to login after 5 attempts")

                assert login_url.host is not None

                text = await self.client.get_text(self.domain, login_url)
                if '<span class="p-navgroup-user-linkText">' in text or "You are already logged in." in text:
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
                if '<span class="p-navgroup-user-linkText">' not in text or "You are already logged in." not in text:
                    continue
                self.logged_in = True
                break
            except asyncio.exceptions.TimeoutError:
                continue

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_complete_from_referer(self, scrape_item: ScrapeItem) -> bool:
        """Checks if the scrape item has already been scraped"""
        check_complete = await self.manager.db_manager.history_table.check_complete_by_referer(self.domain, scrape_item.url)
        if check_complete:
            await log(f"Skipping {scrape_item.url} as it has already been downloaded", 10)
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return True
        return False
    
    async def get_album_results(self, album_id: str) -> bool | dict[Any, Any]:
        """Checks whether an album has completed given its domain and album id"""
        return await self.manager.db_manager.history_table.check_album(self.domain, album_id)
    
    async def check_album_results(self, url: URL, album_results: dict[Any, Any]) -> bool:
        """Checks whether an album has completed given its domain and album id"""
        url_path = await get_db_path(url.with_query(""), self.domain)
        if album_results and url_path in album_results:
            if album_results[url_path] != 0:
                await log(f"Skipping {url} as it has already been downloaded", 10)
                await self.manager.progress_manager.download_progress.add_previously_completed()
                return True
        return False

    async def create_scrape_item(self, parent_scrape_item: ScrapeItem, url: URL, new_title_part: str,
                                 part_of_album: bool = False, album_id: Union[str, None] = None,
                                 possible_datetime: Optional[int] = None) -> ScrapeItem:
        """Creates a scrape item"""
        scrape_item = copy.deepcopy(parent_scrape_item)
        scrape_item.url = url
        if new_title_part:
            await scrape_item.add_to_parent_title(new_title_part)
        scrape_item.part_of_album = part_of_album if part_of_album else scrape_item.part_of_album
        if possible_datetime:
            scrape_item.possible_datetime = possible_datetime
        if album_id:
            scrape_item.album_id = album_id
        return scrape_item

    async def create_title(self, title: str, album_id: Optional[str], thread_id: Optional[str]) -> str:
        """Creates the title for the scrape item"""
        if not title:
            title = "Untitled"

        title = title.strip()
        if self.manager.config_manager.settings_data['Download_Options']['include_album_id_in_folder_name'] and album_id:
            title = f"{title} {album_id}"

        if self.manager.config_manager.settings_data['Download_Options']['include_thread_id_in_folder_name'] and thread_id:
            title = f"{title} {thread_id}"

        if not self.manager.config_manager.settings_data['Download_Options']['remove_domains_from_folder_names']:
            title = f"{title} ({self.folder_domain})"

        return title
