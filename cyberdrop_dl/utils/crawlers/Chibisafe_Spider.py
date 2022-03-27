import logging

import tldextract
from bs4 import BeautifulSoup

from ..base_functions import *
from ..data_classes import *


logger = logging.getLogger(__name__)


class ChibisafeCrawler():
    def __init__(self, *, include_id=False, **kwargs):
        self.include_id = include_id

    async def fetch(self, session, url):
        url_extract = tldextract.extract(url)
        base_domain = "{}.{}".format(url_extract.domain, url_extract.suffix)
        domain_obj = DomainItem(base_domain, {})
        cookies = []

        try:
            async with session.get(url) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                title = soup.select_one("h1[id=title]").get_text()
                if title is None:
                    title = response.url.split('/')[-1]
                elif self.include_id:
                    titlep2 = response.url.split('/')
                    titlep2 = [s for s in titlep2 if "." in s][-1]
                    title = title + " - " + titlep2
                title = make_title_safe(title.replace(r"\n", "").strip())

                links = soup.select("a[class=image]")
                for link in links:
                    link = link.get('href')
                    domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            logger.debug(e)

        return domain_obj, cookies
