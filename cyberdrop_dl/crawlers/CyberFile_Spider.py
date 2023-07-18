from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Tuple, List

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class CyberFileCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.load_files = URL('https://cyberfile.me/account/ajax/load_files')
        self.file_details = URL('https://cyberfile.me/account/ajax/file_details')
        self.limiter = AsyncLimiter(50, 1)
        self.semaphore = asyncio.Semaphore(1)

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director for cyberfile scraping"""
        async with self.semaphore:
            log(f"Starting: {url}", quiet=self.quiet, style="green")
            domain_obj = DomainItem("cyberfile", {})

            # temporary fix for cyberfile.is links
            url = url.with_host("cyberfile.me")

            download_links = []
            if 'folder' in url.parts:
                Folder_ID = await self.get_folder_id(session, url)
                Content_IDs = None
                if Folder_ID:
                    Content_IDs = await self.get_folder_content(session, url, Folder_ID, 1)
                if Content_IDs:
                    download_links = await self.get_download_links(session, url, Content_IDs)
            elif 'shared' in url.parts:
                Node_IDs, Content_IDs = await self.get_shared_ids_and_content(session, url, 1)
                for title, Node_ID in Node_IDs:
                    Content_IDs.extend(await self.get_shared_content(session, url, Node_ID, 1, title))
                download_links = await self.get_download_links(session, url, Content_IDs)
            else:
                Content_ID = await self.get_single_contentId(session, url)
                if Content_ID:
                    download_links = await self.get_download_links(session, url, [("Loose CyberFile Files", Content_ID)])

        for title, media_item in download_links:
            await domain_obj.add_media(title, media_item)
        await self.SQL_Helper.insert_domain("cyberfile", url, domain_obj)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return domain_obj

    async def get_folder_id(self, session: ScrapeSession, url: URL) -> int:
        """Gets the internal ID for a folder"""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            script_func = soup.select_one('div[class="page-container horizontal-menu with-sidebar fit-logo-with-sidebar logged-out clear-adblock"] script').text
            script_func = script_func.split('loadImages(')[-1]
            script_func = script_func.split(';')[0]
            nodeId = int(script_func.split(',')[1].replace("'", ""))
            return nodeId

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return 0

    async def get_folder_content(self, session: ScrapeSession, url: URL, nodeId: int, page: int, title=None):
        """Gets the content id's encased in a folder"""
        data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
        nodes = []
        contents = []
        try:
            async with self.limiter:
                content = await session.post(self.load_files, data)
            text = content['html']
            original_title = title
            if title:
                title = title + "/" + await make_title_safe(content['page_title'])
            else:
                title = content['page_title']
                title = await make_title_safe(title)

            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            pages_tag = soup.select("a[onclick*=loadImages]")[-1]
            assert pages_tag is not None
            pages_str = pages_tag.get('onclick')
            assert isinstance(pages_str, str)
            total_pages = int(pages_str.split(',')[2].split(")")[0].strip())
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                with contextlib.suppress(TypeError):
                    folder_id = listing.get('folderid')
                    if not folder_id:
                        continue
                    assert isinstance(folder_id, str)
                    nodes.append(int(folder_id))

            for listing in listings:
                with contextlib.suppress(TypeError):
                    file_id = listing.get('fileid')
                    if not file_id:
                        continue
                    assert isinstance(file_id, str)
                    contents.append((title, int(file_id)))

            if page < total_pages:
                contents.extend(await self.get_folder_content(session, url, nodeId, page+1, original_title))
            for node in nodes:
                contents.extend(await self.get_folder_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return []

    async def get_single_contentId(self, session: ScrapeSession, url: URL) -> int:
        """Gets an individual content id"""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            script_funcs = soup.select('script')
            for script in script_funcs:
                script_text = script.text
                if script_text and "showFileInformation" in script_text:
                    part_a = script_text.split("showFileInformation(")
                    part_a = [x for x in part_a if x[0].isdigit()][0]
                    part_b = part_a.split(");")[0]
                    contentId = int(part_b)
                    return contentId
            return 0

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return 0

    async def get_shared_ids_and_content(self, session: ScrapeSession, url: URL, page: int) -> Tuple[List, List]:
        """Gets folder id's and content id's from shared links"""
        try:
            # Initial page load to tell server, this is what we want.
            async with self.limiter:
                await session.get_no_resp(url, {'referer': str(url), "user-agent": session.client.user_agent})

            # get the content listings
            data = {"pageType": "nonaccountshared", "nodeId": '', "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            nodes = []
            contents = []

            async with self.limiter:
                content = await session.post(self.load_files, data)
            text = content['html']
            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            page_tag = soup.select_one('input[id=rspTotalPages]')
            assert page_tag is not None
            page_str = page_tag.get('value')
            assert isinstance(page_str, str)
            total_pages = int()
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                title = await make_title_safe(content['page_title'])
                with contextlib.suppress(TypeError, AttributeError, AssertionError):
                    folder_tag = listing.select_one('span[class=filename]')
                    assert folder_tag is not None
                    folder_name = folder_tag.text
                    assert isinstance(folder_name, str)
                    title = title + '/' + await make_title_safe(folder_name)
                    folder_id = listing.get('folderid')
                    assert isinstance(folder_id, str)
                    nodes.append((title, int(folder_id)))

                with contextlib.suppress(TypeError, AttributeError, AssertionError):
                    file_id = listing.get('fileid')
                    assert isinstance(file_id, str)
                    contents.append((title, int(file_id)))

            if page < total_pages:
                nodes_temp, content_temp = await self.get_shared_ids_and_content(session, url, page + 1)
                nodes.extend(nodes_temp)
                contents.extend(content_temp)
            return nodes, contents

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return [], []

    async def get_shared_content(self, session, url: URL, nodeId: int, page: int, title=None) -> List:
        """Gets content from shared folders"""
        try:
            nodes = []
            contents = []
            data = {"pageType": "nonaccountshared", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}

            async with self.limiter:
                content = await session.post(self.load_files, data)
            text = content['html']
            title = title if title else content['page_title']
            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')

            page_ref = soup.select("a[onclick*=loadImages]")[-1].get('onclick')
            assert isinstance(page_ref, str)
            total_pages = int(page_ref.split(',')[2].split(")")[0].strip())

            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                with contextlib.suppress(TypeError, AttributeError):
                    filename = listing.select_one('span[class=filename]')
                    if filename:
                        temp_title = title + '/' + await make_title_safe(filename.text)

                    folder_id = listing.get('folderid')
                    if folder_id:
                        assert isinstance(folder_id, str)
                        nodes.append((temp_title, int(folder_id)))

                with contextlib.suppress(TypeError):
                    file_id = listing.get('fileid')
                    if file_id:
                        assert isinstance(file_id, str)
                        contents.append((title, int(file_id)))

            if page < total_pages:
                contents.extend(await self.get_shared_content(session, url, nodeId, page + 1, title))
            for title, node in nodes:
                contents.extend(await self.get_shared_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return []

    async def get_download_links(self, session: ScrapeSession, url: URL, contentIds: List) -> List:
        """Obtains download links from content ids"""
        download_links = []
        try:
            for title, contentId in contentIds:
                data = {"u": contentId}
                async with self.limiter:
                    content = await session.post(self.file_details, data)
                text = content['html']
                soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
                menu = soup.select_one('ul[class="dropdown-menu dropdown-info account-dropdown-resize-menu"] li a')
                button = soup.select_one('div[class="btn-group responsiveMobileMargin"] button')

                if menu:
                    html_download_text = menu.get("onclick")
                else:
                    assert button is not None
                    html_download_text = button.get("onclick")
                assert isinstance(html_download_text, str)
                link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "cyberfile")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue

                download_links.append((title, media))
            return download_links

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return []
