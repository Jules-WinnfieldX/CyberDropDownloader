import json

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, FILE_FORMATS
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class BunkrCrawler:
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        ext = '.' + str(url).split('.')[-1]
        if ext in FILE_FORMATS['Videos']:
            url = URL(str(url).replace('https://cdn.bunkr.is/', 'https://stream.bunkr.is/v/'))

        if await check_direct(url):
            await domain_obj.add_to_album(link=url, referral=url, title="Bunkr Loose Files")
            return domain_obj

        if "stream.bunkr." in url.host:
            link = await self.stream(session, url)
            await domain_obj.add_to_album(link=link, referral=url, title="Bunkr Loose Files")
            await log("Finished scrape of " + str(url))
            return domain_obj

        await log("Starting scrape of " + str(url))

        try:
            soup = await session.get_BS4(url)
            build_id = json.loads(soup.select_one("script[id=__NEXT_DATA__]").get_text())
            try:
                files = build_id['props']['pageProps']['album']['files']
                json_obj = build_id['props']['pageProps']
            except KeyError:
                json_fetch = URL("https://" + url.host + "/_next/data/" + build_id['buildId'] + url.path + '.json')
                text = await session.get_text(json_fetch)
                json_obj = json.loads(text)['pageProps']
            title = await make_title_safe(json_obj['album']['name'])
            for file in json_obj['album']['files']:
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

        await log("Finished scrape of " + str(url))

        return domain_obj

    async def stream(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            json_obj = json.loads(soup.select_one("script[id=__NEXT_DATA__]").text)
            if not json_obj['props']['pageProps']:
                raise Exception("Couldn't get link from HTML")
            link = URL(json_obj['props']['pageProps']['file']['mediafiles'] + '/' + json_obj['props']['pageProps']['file']['name'])
            return link

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)