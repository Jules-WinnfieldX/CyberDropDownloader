from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class CyberFileCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.load_files = URL('https://cyberfile.me/account/ajax/load_files')
        self.file_details = URL('https://cyberfile.me/account/ajax/file_details')

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director for cyberfile scraping"""
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        domain_obj = DomainItem("cyberfile", {})

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
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return domain_obj

    async def get_folder_id(self, session: ScrapeSession, url: URL):
        """Gets the internal ID for a folder"""
        try:
            soup = await session.get_BS4(url)
            script_func = soup.select_one('div[class="page-container horizontal-menu with-sidebar fit-logo-with-sidebar logged-out clear-adblock"] script').text
            script_func = script_func.split('loadImages(')[-1]
            script_func = script_func.split(';')[0]
            nodeId = int(script_func.split(',')[1].replace("'", ""))
            return nodeId

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return 0

    async def get_folder_content(self, session, url: URL, nodeId, page, title=None):
        """Gets the content id's encased in a folder"""
        data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
        nodes = []
        contents = []
        try:
            content = await session.post(self.load_files, data)
            text = content['html']
            original_title = title
            if title:
                title = title + "/" + await make_title_safe(content['page_title'])
            else:
                title = content['page_title']
                title = await make_title_safe(title)


            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            total_pages = int(soup.select("a[onclick*=loadImages]")[-1].get('onclick').split(',')[2])
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                with contextlib.suppress(TypeError):
                    nodes.append(int(listing.get('folderid')))

                with contextlib.suppress(TypeError):
                    contents.append((title, int(listing.get('fileid'))))

            if page < total_pages:
                contents.extend(await self.get_folder_content(session, url, nodeId, page+1, original_title))
            for node in nodes:
                contents.extend(await self.get_folder_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return []

    async def get_single_contentId(self, session: ScrapeSession, url: URL):
        """Gets an individual content id"""
        try:
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
            return None

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return 0

    async def get_shared_ids_and_content(self, session: ScrapeSession, url: URL, page):
        """Gets folder id's and content id's from shared links"""
        try:
            # Initial page load to tell server, this is what we want.
            await session.get_no_resp(url, {'referer': str(url), "user-agent": session.client.user_agent})

            # get the content listings
            data = {"pageType": "nonaccountshared", "nodeId": '', "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            nodes = []
            contents = []

            content = await session.post(self.load_files, data)
            text = content['html']
            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            total_pages = int(soup.select_one('input[id=rspTotalPages]').get('value'))
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                title = await make_title_safe(content['page_title'])
                with contextlib.suppress(TypeError, AttributeError):
                    title = title + '/' + await make_title_safe(listing.select_one('span[class=filename]').text)
                    nodes.append((title, int(listing.get('folderid'))))

                with contextlib.suppress(TypeError):
                    contents.append((title, int(listing.get('fileid'))))

            if page < total_pages:
                nodes_temp, content_temp = await self.get_shared_ids_and_content(session, url, page + 1)
                nodes.extend(nodes_temp)
                contents.extend(content_temp)
            return nodes, contents

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return []

    async def get_shared_content(self, session, url: URL, nodeId, page, title=None):
        """Gets content from shared folders"""
        try:
            nodes = []
            contents = []
            data = {"pageType": "nonaccountshared", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}

            content = await session.post(self.load_files, data)
            text = content['html']

            title = title if title else content['page_title']

            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            total_pages = int(soup.select("a[onclick*=loadImages]")[-1].get('onclick').split(',')[2])
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                with contextlib.suppress(TypeError, AttributeError):
                    filename = listing.select_one('span[class=filename]')
                    temp_title = title + '/' + await make_title_safe(filename.text)
                    nodes.append((temp_title, int(listing.get('folderid'))))

                with contextlib.suppress(TypeError):
                    contents.append((title, int(listing.get('fileid'))))

            if page < total_pages:
                contents.extend(await self.get_shared_content(session, url, nodeId, page + 1, title))
            for title, node in nodes:
                contents.extend(await self.get_shared_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return []

    async def get_download_links(self, session, url, contentIds):
        """Obtains download links from content ids"""
        download_links = []
        try:
            for title, contentId in contentIds:
                data = {"u": contentId}
                content = await session.post(self.file_details, data)
                text = content['html']
                soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
                menu = soup.select_one('ul[class="dropdown-menu dropdown-info account-dropdown-resize-menu"] li a')
                button = soup.select_one('div[class="btn-group responsiveMobileMargin"] button')

                if menu:
                    html_download_text = menu.get("onclick")
                    link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                elif button:
                    html_download_text = button.get("onclick")
                    link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "cyberfile")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue

                download_links.append((title, media))
            return download_links

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return []
