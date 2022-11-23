import http
from typing import Union

from gofile import Gofile
from yarl import URL

from ..base_functions.base_functions import log
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class GofileCrawler():
    def __init__(self, quiet: bool):
        self.quiet = quiet
        self.client = Gofile()

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem('gofile.io', {})

        # Set cookie in cookie_jar
        client_token = self.client.token
        morsel = http.cookies.Morsel()
        morsel['domain'] = 'gofile.io'
        morsel.set('accountToken', client_token, client_token)
        session.client_session.cookie_jar.update_cookies({'gofile.io': morsel})

        results = await self.get_links(url)

        await log("Starting scrape of " + str(url), quiet=self.quiet)

        if results:
            for result in results:
                await domain_obj.add_to_album(result['title'], result['url'], result['referral'])

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def get_links(self, url: URL, og_title=None):
        results = []
        content_id = url.name if url.host == 'gofile.io' else url
        try:
            content = self.client.get_content(content_id)
        except:
            await log("Error scraping " + str(url), quiet=self.quiet)
            return
        if not content:
            return

        title = content["name"]
        if og_title is not None:
            title = og_title + '/' + title

        contents: dict[str, dict[str, Union[str, int]]] = content["contents"]
        for val in contents.values():
            if val["type"] == "folder":
                try:
                    results.extend(result for result in await self.get_links(URL(val["code"]), title))
                except Exception as e:
                    await log(f"Error scraping gofile: {val['code']}", quiet=self.quiet)
            else:
                results.append({'url': URL(val["link"]) if val["link"] != "overloaded" else URL(val["directLink"]),
                                'title': title, 'referral': URL('https://gofile.io/')})
        return results
