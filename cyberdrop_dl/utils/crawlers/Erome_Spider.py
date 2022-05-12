from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, logger, make_title_safe, ssl_context
from ..data_classes import DomainItem


class EromeCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), Fore.WHITE)

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
                title = await make_title_safe(title)

                # Images
                for link in soup.select('img[class="img-front lasyload"]'):
                    await domain_obj.add_to_album(title, URL(link['data-src']), url)

                # Videos
                for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                    await domain_obj.add_to_album(title, URL(link['src']), url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj
