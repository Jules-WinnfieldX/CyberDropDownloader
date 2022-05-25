from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL
import json

from ..base_functions import bunkr_parse, log, logger, make_title_safe, ssl_context, check_direct
from ..data_classes import DomainItem


class BunkrCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        domain_obj = DomainItem(url.host, {})

        if await check_direct(url):
            link = await bunkr_parse(url)
            await domain_obj.add_to_album(link=link, referral=url, title="Bunkr Loose Files")
            return domain_obj

        await log("Starting scrape of " + str(url), Fore.WHITE)

        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                build_id = json.loads(soup.select_one("script[id=__NEXT_DATA__]").get_text())

            json_fetch = URL("https://" + url.host + "/_next/data/" + build_id['buildId'] + url.path + '.json')
            async with session.get(json_fetch, ssl=ssl_context) as response:
                text = await response.text()
                json_obj = json.loads(text)['pageProps']
                title = await make_title_safe(json_obj['album']['name'])
                for file in json_obj['files']:
                    if 'video' in file['type']:
                        link = URL(file['node_mediafiles'] + '/' + file['name'])
                    else:
                        link = URL(file['node_cdn'] + '/' + file['name'])
                    await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj
