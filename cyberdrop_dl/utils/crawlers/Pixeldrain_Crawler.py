import json

from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, ssl_context, user_agent, logger
from ..data_classes import DomainItem


class PixelDrainCrawler:
    def __init__(self):
        self.api = URL('https://pixeldrain.com/api/')

    async def create_download_link(self, file):
        final_url = (URL('https://pixeldrain.com/api/file/') / file).with_query('download')
        return final_url

    async def get_listings(self, session, identifier, url):
        links = []
        try:
            async with session.get(self.api / "list" / identifier, headers={"user-agent": user_agent}, ssl=ssl_context) as response:
                content = json.loads(await response.content.read())
                for file in content['files']:
                    links.append(await self.create_download_link(file['id']))
            return links
        except Exception as e:
            await log("Error scraping " + str(url))
            logger.debug(e)
            return None

    async def fetch(self, session, url):
        await log("Starting scrape of " + str(url), Fore.WHITE)
        domain_obj = DomainItem("pixeldrain.com", {})

        identifier = str(url).split('/')[-1]
        if url.parts[1] == 'l':
            links = await self.get_listings(session, identifier, url)
            if links:
                for link in links:
                    await domain_obj.add_to_album(identifier, link, url)
        else:
            link = await self.create_download_link(identifier)
            await domain_obj.add_to_album("Loose Pixeldrain Files", link, url)

        await log("Finished scrape of " + str(url), Fore.WHITE)
        return domain_obj