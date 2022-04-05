import http
from typing import Union

from gofile import Gofile

from ..data_classes import *
from ..base_functions import *


class GofileCrawler():
    def __init__(self):
        self.client = Gofile()

    async def fetch(self, session, url):
        domain_obj = DomainItem('gofile.io', {})

        # Set cookie in cookie_jar
        client_token = self.client.token
        morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.cookie_jar.update_cookies({'gofile.io': morsel})

        results = await self.get_links(url)

        log("Starting scrape of " + str(url), Fore.WHITE)
        logging.debug("Starting scrape of " + str(url))

        if results:
            for result in results:
                domain_obj.add_to_album(result['title'], result['url'], result['referral'])

        log("Finished scrape of " + str(url), Fore.WHITE)
        logging.debug("Finished scrape of " + str(url))

        return domain_obj

    async def get_links(self, url, og_title=None):
        results = []
        content_id = url.name if url.host == 'gofile.io' else url
        try:
            content = self.client.get_content(content_id)
        except:
            log("GoFile seems to be down.")
            logging.debug("GoFile seems to be down")
            return
        if not content:
            return

        title = content["name"]
        if og_title is not None:
            title = og_title + '/' + title

        contents: dict[str, dict[str, Union[str, int]]] = content["contents"]
        for val in contents.values():
            if val["type"] == "folder":
                results.extend(result for result in await self.get_links(URL(val["code"]), title))
            else:
                results.append({'url': URL(val["link"]) if val["link"] != "overloaded" else URL(val["directLink"]),
                                'title': title, 'referral': URL('https://gofile.io/')})
        return results
