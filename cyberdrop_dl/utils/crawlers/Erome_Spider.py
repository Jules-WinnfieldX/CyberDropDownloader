from bs4 import BeautifulSoup

from ..base_functions import *
from ..data_classes import *


class EromeCrawler():
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

                # Title
                title = soup.select_one('div[class="col-sm-12 page-content"] h1').get_text()
                if title is None:
                    title = url.name
                elif self.include_id:
                    title = title + " - " + url.name
                title = make_title_safe(title)

                # Images
                for link in soup.select('img[class="img-front lasyload"]'):
                    domain_obj.add_to_album(title, URL(link['data-src']), url)

                # Videos
                for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                    domain_obj.add_to_album(title, URL(link['src']), url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)

        log("Finished scrape of " + str(url), Fore.WHITE)
        logging.debug("Finished scrape of " + str(url))

        return domain_obj
