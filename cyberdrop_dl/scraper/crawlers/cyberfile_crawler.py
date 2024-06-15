from __future__ import annotations

import calendar
import datetime
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from cyberdrop_dl.clients.errors import PasswordProtected, ScrapeFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, log, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class CyberfileCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "cyberfile", "Cyberfile")
        self.api_files = URL('https://cyberfile.me/account/ajax/load_files')
        self.api_details = URL('https://cyberfile.me/account/ajax/file_details')
        self.request_limiter = AsyncLimiter(5, 1)

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
            soup = await self.client.get_BS4(self.domain, scrape_item.url)
        script_func = soup.select('div[class*="page-container"] script')[-1].text
        script_func = script_func.split('loadImages(')[-1]
        script_func = script_func.split(';')[0]
        nodeId = int(script_func.split(',')[1].replace("'", ""))

        page = 1
        while True:
            data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            async with self.request_limiter:
                ajax_dict = await self.client.post_data(self.domain, self.api_files, data=data)
                ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')
            title = await self.create_title(ajax_dict['page_title'], scrape_item.url.parts[2], None)
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
                    await log(f"Couldn't find folder or file id for {scrape_item.url} element", 30)
                    continue

                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
                self.manager.task_group.create_task(self.run(new_scrape_item))

            page += 1
            if page > num_pages:
                break

    @error_handling_wrapper
    async def shared(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a shared folder"""
        async with self.request_limiter:
            await self.client.get_BS4(self.domain, scrape_item.url)

        new_folders = []
        node_id = ''

        page = 1
        while True:
            data = {"pageType": "nonaccountshared", "nodeId": node_id, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            async with self.request_limiter:
                ajax_dict = await self.client.post_data("cyberfile", self.api_files, data=data)
                ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')
            title = await self.create_title(ajax_dict['page_title'], scrape_item.url.parts[2], None)
            num_pages = int(ajax_soup.select_one('input[id=rspTotalPages]').get('value'))

            tile_listings = ajax_soup.select("div[class=fileListing] div[class*=fileItem]")
            for tile in tile_listings:
                folder_id = tile.get('folderid')
                file_id = tile.get('fileid')

                if folder_id:
                    new_folders.append(folder_id)
                    continue
                elif file_id:
                    link = URL(tile.get('dtfullurl'))
                else:
                    await log(f"Couldn't find folder or file id for {scrape_item.url} element", 30)
                    continue

                new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True)
                self.manager.task_group.create_task(self.run(new_scrape_item))

            page += 1
            if page > num_pages and not new_folders:
                break

            if page > num_pages and new_folders:
                node_id = str(new_folders.pop(0))
                page = 1

    @error_handling_wrapper
    async def file(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a file"""
        async with self.request_limiter:
            soup = await self.client.get_BS4(self.domain, scrape_item.url)

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
        """Scrapes a file using the content id"""
        data = {"u": contentId}
        async with self.request_limiter:
            ajax_dict = await self.client.post_data(self.domain, self.api_details, data=data)
            ajax_soup = BeautifulSoup(ajax_dict['html'].replace("\\", ""), 'html.parser')
            
        if "albumPasswordModel" in ajax_dict['html']:
            await log(f"Album is password protected: {scrape_item.url}", 30)
            raise PasswordProtected()

        file_menu = ajax_soup.select_one('ul[class="dropdown-menu dropdown-info account-dropdown-resize-menu"] li a')
        file_button = ajax_soup.select_one('div[class="btn-group responsiveMobileMargin"] button')
        try:
            if file_menu:
                html_download_text = file_menu.get("onclick")
            else:
                html_download_text = file_button.get("onclick")
        except AttributeError:
            await log(f"Couldn't find download button for {scrape_item.url}", 30)
            raise ScrapeFailure(422, "Couldn't find download button")
        link = URL(html_download_text.split("'")[1])

        file_detail_table = ajax_soup.select('table[class="table table-bordered table-striped"]')[-1]
        uploaded_row = file_detail_table.select('tr')[-2]
        uploaded_date = uploaded_row.select_one('td[class=responsiveTable]').text.strip()
        uploaded_date = await self.parse_datetime(uploaded_date)
        scrape_item.possible_datetime = uploaded_date

        filename, ext = await get_filename_and_ext(link.name)
        await self.handle_file(link, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def parse_datetime(self, date: str) -> int:
        """Parses a datetime string into a unix timestamp"""
        date = datetime.datetime.strptime(date, "%d/%m/%Y %H:%M:%S")
        return calendar.timegm(date.timetuple())
