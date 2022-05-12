from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, logger, ssl_context
from ..data_classes import DomainItem


class AnonfilesCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), Fore.WHITE)

        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                title = "Anonfiles"

                link = soup.select_one("a[id=download-url]")
                link = URL(link.get('href'))
                await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj
