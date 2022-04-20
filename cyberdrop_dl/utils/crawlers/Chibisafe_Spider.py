from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import bunkr_parse, log, logger, make_title_safe, ssl_context, check_direct
from ..data_classes import DomainItem


class ChibisafeCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        domain_obj = DomainItem(url.host, {})

        if await check_direct(url):
            if "bunkr" in url.host:
                link = await bunkr_parse(url)
            else:
                link = URL(url)
            await domain_obj.add_to_album(link=link, referral=url, title="Chibisafe Loose Files")
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

                links = soup.select("a[class=image]")
                for link in links:
                    link = URL(link.get('href'))
                    if 'bunkr' in link.host:
                        link = await bunkr_parse(link)
                    await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj
