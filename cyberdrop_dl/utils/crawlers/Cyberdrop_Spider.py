from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, logger, make_title_safe, ssl_context, check_direct
from ..data_classes import DomainItem


class CyberdropCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        domain_obj = DomainItem(url.host, {})

        if await check_direct(url):
            link = URL(url)
            await domain_obj.add_to_album(link=link, referral=url, title="Cyberdrop Loose Files")
            return domain_obj

        await log("Starting scrape of " + str(url), Fore.WHITE)

        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                title = soup.select_one("h1[id=title]").get_text()
                if title is None:
                    title = url.name
                elif self.include_id:
                    titlep2 = url.name
                    titlep2 = [s for s in titlep2 if "." in s][-1]
                    title = title + " - " + titlep2
                title = await make_title_safe(title.replace(r"\n", "").strip())

                links = soup.select('div[class="image-container column"] a')
                for link in links:
                    link = URL(link.get('href'))
                    await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj
