import asyncio
import re

from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, logger, ssl_context, make_title_safe
from ..data_classes import DomainItem


class KemonoCrawler:
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url: URL):
        await log("Starting scrape of " + str(url), Fore.WHITE)
        domain_obj = DomainItem('kemono.party', {})
        results = []

        if "thumbnail" in url.parts:
            parts = [x for x in url.parts if x != "thumbnail" and x != "/"]
            link = URL("https://kemono.party/" + "/".join(parts))
            await domain_obj.add_to_album("Loose Kemono.Party Files", link, link)
        elif "data" in url.parts:
            await domain_obj.add_to_album("Loose Kemono.Party Files", url, url)
        else:
            results.extend(await self.parse_profile(session, url))

        for result in results:
            await domain_obj.add_to_album(result[0], result[1], result[2])

        await log("Finished scrape of " + str(url), Fore.WHITE)
        return domain_obj

    async def parse_profile(self, session, url: URL):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                title = soup.select_one("span[itemprop=name]").get_text()
                title = title + " (Kemono.party)"
                results = []

                posts = soup.select("a[class=fancy-link]")
                for post in posts:
                    path = post.get('href')
                    if path:
                        post_link = URL("https://kemono.party" + path)
                        results.extend(await self.parse_post(session, post_link, title))

                next_page = soup.select_one('a[title="Next page"]')
                if next_page:
                    next_page = next_page.get('href')
                    if next_page:
                        results.extend(await self.parse_profile(session, URL("https://kemono.party" + next_page)))
                return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []

    async def parse_post(self, session, url: URL, title: str):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                results = []

                title = title + '/' + await make_title_safe(soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", ""))

                images = soup.select('a[class="fileThumb"]')
                for image in images:
                    image_link = URL("https://kemono.party" + image.get('href'))
                    results.append([title, image_link, url])

                downloads = soup.select('a[class=post__attachment-link]')
                for download in downloads:
                    download_link = URL("https://kemono.party" + download.get('href'))
                    results.append([title, download_link, url])

                return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
            return []