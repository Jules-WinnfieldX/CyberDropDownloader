import json

from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, ssl_context, user_agent, logger
from ..data_classes import DomainItem


class CyberfileCrawler:
    def __init__(self):
        self.load_files = URL('https://cyberfile.is/account/ajax/load_files')
        self.file_details = URL('https://cyberfile.is/account/ajax/file_details')

    async def folder_nodeId(self, session, url: URL):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                script_func = soup.select_one('div[class="page-container horizontal-menu with-sidebar fit-logo-with-sidebar logged-out clear-adblock"] script').text
                script_func = script_func.split('loadImages(')[-1]
                script_func = script_func.split(';')[0]
                nodeId = int(script_func.split(',')[1].replace("'", ""))
                return nodeId

        except Exception as e:
            await log("Error scraping " + str(url))
            logger.debug(e)
            return 0

    async def get_single_contentId(self, session, url: URL):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
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
            await log("Error scraping " + str(url))
            logger.debug(e)
            return 0

    async def shared_nodeId_root_content(self, session, url: URL, page):
        try:
            # Initial page load to tell server, this is what we want.
            async with session.get(str(url), headers={'referer': str(url), "user-agent": user_agent}, ssl=ssl_context) as response:
                pass

            # get the content listings
            data = {"pageType": "nonaccountshared", "nodeId": '', "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            nodes = []
            contents = []
            async with session.post(self.load_files, data=data, headers={"user-agent": user_agent}, ssl=ssl_context) as response:
                content = json.loads(await response.content.read())
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
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []

    async def shared_content(self, session, url: URL, nodeId, page, title=None):
        try:
            nodes = []
            contents = []
            data = {"pageType": "nonaccountshared", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
            async with session.post(self.load_files, data=data, headers={"user-agent": user_agent}, ssl=ssl_context) as response:
                content = json.loads(await response.content.read())
                text = content['html']
                title = title if title else content['page_title']
                soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
                total_pages = int(soup.select_one('input[id=rspTotalPages]').get('value'))
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
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []

    async def folder_content(self, session, url: URL, nodeId, page):
        data = {"pageType": "folder", "nodeId": nodeId, "pageStart": page, "perPage": 0, "filterOrderBy": ""}
        nodes = []
        contents = []
        try:
            async with session.post(self.load_files, data=data, headers={"user-agent": user_agent}, ssl=ssl_context) as response:
                content = json.loads(await response.content.read())
                text = content['html']
                title = content['page_title']
                soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
                total_pages = int(soup.select_one('input[id=rspTotalPages]').get('value'))
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
                contents.extend(await self.folder_content(session, url, node, 1))
            return contents

        except Exception as e:
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []

    async def get_download_links(self, session, url, contentIds):
        download_links = []
        try:
            for title, contentId in contentIds:
                data = {"u": contentId}
                async with session.post(self.file_details, data=data, headers={"user-agent": user_agent}, ssl=ssl_context) as response:
                    text = await response.text()
                    soup = BeautifulSoup(text.replace("\\", ""), 'html.parser')
                    menu = soup.select_one('ul[class="dropdown-menu dropdown-info account-dropdown-resize-menu"] li a')
                    if menu:
                        html_download_text = menu.get("onclick")
                        link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                        download_links.append((title, link))
                    button = soup.select_one('div[class="btn-group responsiveMobileMargin"] button')
                    if button:
                        html_download_text = button.get("onclick")
                        link = URL(html_download_text.replace("openUrl('", "").replace("'); return false;", ""))
                        download_links.append((title, link))
            return download_links

        except Exception as e:
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []

    async def fetch(self, session, url: URL):
        await log("Starting scrape of " + str(url), Fore.WHITE)
        domain_obj = DomainItem("cyberfile.is", {})
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
        await log("Finished scrape of " + str(url), Fore.WHITE)
        return domain_obj
