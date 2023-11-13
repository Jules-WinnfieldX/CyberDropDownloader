from __future__ import annotations

import calendar
import datetime
from dataclasses import field
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem, MediaItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, log, get_download_path, get_filename_and_ext

if TYPE_CHECKING:
    from asyncio import Queue

    from cyberdrop_dl.clients.scraper_client import ScraperClient
    from cyberdrop_dl.managers.manager import Manager


class CyberfileCrawler:
    def __init__(self, manager: Manager):
        self.manager = manager
        self.scraping_progress = manager.progress_manager.scraping_progress
        self.client: ScraperClient = field(init=False)

        self.api_files = URL('https://cyberfile.me/account/ajax/load_files')
        self.api_details = URL('https://cyberfile.me/account/ajax/file_details')

        self.complete = False

        self.scraped_items: list = []
        self.scraper_queue: Queue = field(init=False)
        self.download_queue: Queue = field(init=False)

        self.request_limiter = AsyncLimiter(5, 1)

    async def startup(self) -> None:
        """Starts the crawler"""
        self.scraper_queue = await self.manager.queue_manager.get_scraper_queue("cyberfile")
        self.download_queue = await self.manager.queue_manager.get_download_queue("cyberfile")

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

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "folder" in scrape_item.url.parts:
            await self.folder(scrape_item)
        elif "shared" in scrape_item.url.parts:
            await self.shared(scrape_item)
        else:
            await self.file(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def folder(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a folder"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("cyberfile", scrape_item.url)
        script_func = soup.select('div[class*="page-container"] script')[-1].text
        script_func = script_func.split('loadImages(')[-1]
        script_func = script_func.split(';')[0]
        nodeId = int(script_func.split(',')[1].replace("'", ""))

        page = 1
        while True:
            data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            async with self.request_limiter:
                ajax_dict = await self.client.post_data("cyberfile", self.api_files, data=data)
                ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')
            title = ajax_dict['page_title']
            num_pages = int(ajax_soup.select("a[onclick*=loadImages]")[-1].get('onclick').split(',')[2].split(")")[0].strip())

            tile_listings = ajax_soup.select("div[class=fileListing] div[class*=fileItem]")
            for tile in tile_listings:
                folder_id = tile.get('folderid')
                file_id = tile.get('fileid')

                if folder_id:
                    link = URL(tile.get('sharing-url'))
                elif file_id:
                    link = URL(tile.get('dtfullurl'))
                else:
                    await log(f"Couldn't find folder or file id for {scrape_item.url} element")
                    continue

                new_scrape_item = ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True)
                await new_scrape_item.add_to_parent_title(title)
                await self.scraper_queue.put(new_scrape_item)

            page += 1
            if page >= num_pages:
                break

    @error_handling_wrapper
    async def shared(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a shared folder"""
        async with self.request_limiter:
            await self.client.get_BS4("cyberfile", scrape_item.url)

        page = 1
        while True:
            data = {"pageType": "nonaccountshared", "nodeId": '', "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            async with self.request_limiter:
                ajax_dict = await self.client.post_data("cyberfile", self.api_files, data=data)
                ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')
            title = ajax_dict['page_title']
            num_pages = int(ajax_soup.select_one('input[id=rspTotalPages]').get('value'))

            tile_listings = ajax_soup.select("div[class=fileListing] div[class*=fileItem]")
            for tile in tile_listings:
                folder_id = tile.get('folderid')
                file_id = tile.get('fileid')

                if folder_id:
                    link = URL(tile.get('sharing-url'))
                elif file_id:
                    link = URL(tile.get('dtfullurl'))
                else:
                    await log(f"Couldn't find folder or file id for {scrape_item.url} element")
                    continue

                new_scrape_item = ScrapeItem(url=link, parent_title=scrape_item.parent_title, part_of_album=True)
                await new_scrape_item.add_to_parent_title(title)
                await self.scraper_queue.put(new_scrape_item)

            page += 1
            if page >= num_pages:
                break

    @error_handling_wrapper
    async def file(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a file"""
        async with self.request_limiter:
            soup = await self.client.get_BS4("cyberfile", scrape_item.url)

        script_funcs = soup.select('script')
        for script in script_funcs:
            script_text = script.text
            if script_text and "showFileInformation" in script_text:
                contentId_a = script_text.split("showFileInformation(")
                contentId_a = [x for x in contentId_a if x[0].isdigit()][0]
                contentId_b = contentId_a.split(");")[0]
                contentId = int(contentId_b)
                await self.handle_content_id(scrape_item, contentId)
                return

    @error_handling_wrapper
    async def handle_content_id(self, scrape_item: ScrapeItem, contentId: int) -> None:
        data = {"u": contentId}
        async with self.request_limiter:
            ajax_dict = await self.client.post_data("cyberfile", self.api_details, data=data)
            ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')

        file_menu = ajax_soup.select_one('ul[class="dropdown-menu dropdown-info account-dropdown-resize-menu"] li a')
        file_button = ajax_soup.select_one('div[class="btn-group responsiveMobileMargin"] button')
        if file_menu:
            html_download_text = file_menu.get("onclick")
        else:
            html_download_text = file_button.get("onclick")
        link = URL(html_download_text.split("'")[1])

        file_detail_table = ajax_soup.select_one('table[class="table table-bordered table-striped"]')
        uploaded_row = file_detail_table.select('tr')[-2]
        uploaded_date = uploaded_row.select_one('td[class=responsiveTable]').text.strip()
        uploaded_date = await self.parse_datetime(uploaded_date)
        scrape_item.possible_datetime = uploaded_date

        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)

    async def handle_file(self, url: URL, scrape_item: ScrapeItem, filename: str, ext: str) -> None:
        """Finishes handling the file and hands it off to the download_queue"""
        check_complete = await self.manager.db_manager.history_table.check_complete("cyberfile", url)
        if check_complete:
            await log(f"Skipping {url} as it has already been downloaded")
            await self.manager.progress_manager.download_progress.add_previously_completed()
            return

        download_folder = await get_download_path(self.manager, scrape_item, "Cyberfile")
        media_item = MediaItem(url, scrape_item.url, download_folder, filename, ext, filename)
        if scrape_item.possible_datetime:
            media_item.datetime = scrape_item.possible_datetime

        await self.download_queue.put(media_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        time = date.split(" ")[1]
        day = date.split(" ")[0].split("/")[0]
        month = date.split(" ")[0].split("/")[1]
        year = date.split(" ")[0].split("/")[2]
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(date.timetuple())
