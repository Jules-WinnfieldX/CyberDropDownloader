from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL
import json

from ..base_functions import log, logger, make_title_safe, ssl_context, check_direct, FILE_FORMATS, user_agent
from ..data_classes import DomainItem


class BunkrCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url: URL):
        domain_obj = DomainItem(url.host, {})

        if await check_direct(url):
            ext = '.' + str(url).split('.')[-1]
            if ext in FILE_FORMATS['Videos']:
                url = URL(str(url).replace('https://cdn', 'https://media-files'))
                await domain_obj.add_to_album(link=url, referral=url, title="Bunkr Loose Files")
                return domain_obj
            else:
                await domain_obj.add_to_album(link=url, referral=url, title="Bunkr Loose Files")
                return domain_obj

        if "stream.bunkr." in url.host:
            link = await self.stream(session, url)
            await domain_obj.add_to_album(link=link, referral=url, title="Bunkr Loose Files")
            await log("Finished scrape of " + str(url), Fore.WHITE)
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
                    ext = '.' + file['name'].split('.')[-1].lower()
                    if ext in FILE_FORMATS['Videos']:
                        cdn_loc = file['cdn']
                        media_loc = cdn_loc.replace('cdn', 'media-files')
                        link = URL(media_loc + '/' + file['name'])
                    else:
                        link = URL(file['cdn'] + '/' + file['name'])
                    await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)

        await log("Finished scrape of " + str(url), Fore.WHITE)

        return domain_obj

    async def stream(self, session, url):
        try:
            async with session.get(url, ssl=ssl_context, headers={'Referer': str(url), 'user-agent': user_agent}) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                json_obj = json.loads(soup.select_one("script[id=__NEXT_DATA__]").text)
                if not json_obj['props']['pageProps']:
                    raise Exception("Couldn't get link from HTML")
                else:
                    link = URL(json_obj['props']['pageProps']['file']['mediafiles'] + '/' + json_obj['props']['pageProps']['file']['name'])
                return link

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
