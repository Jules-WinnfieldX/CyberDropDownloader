from typing import Union

from gofile import Gofile

from ..data_classes import *
from ..base_functions import *


class GofileCrawler():
    def __init__(self):
        self.client = Gofile()

    async def fetch(self, url):
        domain_obj = DomainItem('gofile.io', {})
        cookies = [{'name': 'accountToken', 'value': self.client.token}]
        results = await self.get_links(url)

        log("Starting scrape of " + url, Fore.WHITE)
        logging.debug("Starting scrape of " + url)

        for result in results:
            domain_obj.add_to_album(result['title'], result['url'], result['referral'])

        log("Finished scrape of " + url, Fore.WHITE)
        logging.debug("Finished scrape of " + url)

        return domain_obj, cookies

    async def get_links(self, url, og_title=None):
        results = []
        content_id = url.split("/")[-1] if url.startswith("https://gofile.io/") else url
        content = self.client.get_content(content_id)
        if not content:
            return

        title = content["name"]
        if og_title is not None:
            title = og_title + '/' + title

        contents: dict[str, dict[str, Union[str, int]]] = content["contents"]
        for val in contents.values():
            if val["type"] == "folder":
                results.extend(result for result in await self.get_links(val["code"], title))
            else:
                results.append({'url': val["link"] if val["link"] != "overloaded" else val["directLink"],
                                'title': title, 'referral': 'https://gofile.io/'})
        return results
