import re

from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import log, logger
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class CyberfileCrawler:
    def __init__(self, quiet: bool):
        self.quiet = quiet
        self.load_files = URL('https://cyberfile.su/account/ajax/load_files')
        self.file_details = URL('https://cyberfile.su/account/ajax/file_details')

    async def fetch(self, session: Session, url: URL):
        await log("Starting scrape of " + str(url), quiet=self.quiet)
        domain_obj = DomainItem("cyberfile.su", {})
        download_links = []
        if 'folder' in url.parts:
            nodeId = await self.folder_nodeId(session, url)
            contentIds = await self.folder_content(session, url, nodeId, 1)
            download_links = await self.get_download_links(session, url, contentIds)
        elif 'shared' in url.parts:
            nodeIds, contentIds = await self.shared_nodeId_root_content(session, url, 1)
            for title, nodeId in nodeIds:
                contentIds.extend(await self.shared_content(session, url, nodeId, 1, title))
            download_links = await self.get_download_links(session, url, contentIds)
        else:
            contentId = await self.get_single_contentId(session, url)
            if contentId:
                download_links = await self.get_download_links(session, url, [("Loose Cyberfile Files", contentId)])
        for title, download_link in download_links:
            await domain_obj.add_to_album(title, download_link, url)
        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return domain_obj

    async def folder_nodeId(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            script_func = soup.select_one('div[class="page-container horizontal-menu with-sidebar fit-logo-with-sidebar logged-out clear-adblock"] script').text
            script_func = script_func.split('loadImages(')[-1]
            script_func = script_func.split(';')[0]
            nodeId = int(script_func.split(',')[1].replace("'", ""))
            return nodeId

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return 0

    async def get_single_contentId(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            script_funcs = soup.select('script')
            for script in script_funcs:
                script_text = script.text
                if script_text:
                    if "showFileInformation" in script_text:
                        parta = script_text.split("showFileInformation(")
                        parta = [x for x in parta if x[0].isdigit()][0]
                        partb = parta.split(");")[0]
                        contentId = int(partb)
                        return contentId
            return None

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return 0

    async def shared_nodeId_root_content(self, session: Session, url: URL, page):
        try:
            # Initial page load to tell server, this is what we want.
            await session.post_no_resp(url, {'referer': str(url), "user-agent": session.client.user_agent})

            # get the content listings
            data = {"pageType": "nonaccountshared", "nodeId": '', "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            nodes = []
            contents = []

            content = await session.post(self.load_files, data)
            text = content['html']
            title = content['page_title']
            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            total_pages = int(soup.select_one('input[id=rspTotalPages]').get('value'))
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                title = content['page_title']
                try:
                    title = title + '/' + listing.select_one('span[class=filename]').text
                    nodes.append((title, int(listing.get('folderid'))))
                except (TypeError, AttributeError):
                    pass
                try:
                    contents.append((title, int(listing.get('fileid'))))
                except TypeError:
                    pass

            if page < total_pages:
                nodes_temp, content_temp = await self.shared_nodeId_root_content(session, url, page+1)
                nodes.extend(nodes_temp)
                contents.extend(content_temp)
            return nodes, contents

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []

    async def shared_content(self, session, url: URL, nodeId, page, title=None):
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
                try:
                    nodes.append(int(listing.get('folderid')))
                except TypeError:
                    pass
                try:
                    contents.append((title, int(listing.get('fileid'))))
                except TypeError:
                    pass

            if page < total_pages:
                contents.extend(await self.shared_content(session, url, nodeId, page+1, title))
            for node in nodes:
                contents.extend(await self.shared_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []

    async def folder_content(self, session, url: URL, nodeId, page, title=None):
        data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
        nodes = []
        contents = []
        try:
            content = await session.post(self.load_files, data)
            text = content['html']
            if title:
                title = title + "/" + content['page_title']
            else:
                title = content['page_title']
            soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
            total_pages = int(soup.select("a[onclick*=loadImages]")[-1].get('onclick').split(',')[2])
            listings = soup.select("div[class=fileListing] div")
            for listing in listings:
                try:
                    nodes.append(int(listing.get('folderid')))
                except TypeError:
                    pass
                try:
                    contents.append((title, int(listing.get('fileid'))))
                except TypeError:
                    pass

            if page < total_pages:
                contents.extend(await self.folder_content(session, url, nodeId, page+1))
            for node in nodes:
                contents.extend(await self.folder_content(session, url, node, 1, title))
            return contents

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []

    async def get_download_links(self, session, url, contentIds):
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
                    download_links.append((title, link))
                elif button:
                    html_download_text = button.get("onclick")
                    link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                    download_links.append((title, link))
            return download_links

        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []
