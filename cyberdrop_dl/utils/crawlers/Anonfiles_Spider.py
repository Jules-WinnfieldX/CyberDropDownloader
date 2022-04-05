from bs4 import BeautifulSoup

from ..base_functions import *
from ..data_classes import *


class AnonfilesCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        url_extract = tldextract.extract(str(url))
        base_domain = "{}.{}".format(url_extract.domain, url_extract.suffix)
        domain_obj = DomainItem(base_domain, {})

        log("Starting scrape of " + str(url), Fore.WHITE)
        logging.debug("Starting scrape of " + str(url))

        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                title = "Anonfiles"

                link = soup.select_one("a[id=download-url]")
                link = URL(link.get('href'))
                domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)

        log("Finished scrape of " + str(url), Fore.WHITE)
        logging.debug("Finished scrape of " + str(url))

        return domain_obj
