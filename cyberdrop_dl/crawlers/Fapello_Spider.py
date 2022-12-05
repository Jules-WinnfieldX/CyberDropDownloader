from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class FapelloCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        await log("Starting scrape of " + str(url), quiet=self.quiet)
        domain_obj = DomainItem('fapello', {})
        results = []

        results.extend(await self.parse_profile(session, url))

        for result in results:
            await domain_obj.add_to_album(result[0], result[1], result[2])

        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return domain_obj

    async def parse_profile(self, session: Session, url: URL):
        try:
            soup, returned_url = await session.get_BS4_and_url(url)
            title = soup.select_one('h2[class="font-semibold lg:text-2xl text-lg mb-2 mt-4"]').get_text()
            title = title + " (Fapello)"
            results = []

            # Fapello does circular looped paging
            if returned_url != url:
                return results

            content_section = soup.select_one("div[id=content]")
            posts = content_section.select("a")
            for post in posts:
                link = post.get('href')
                if link:
                    results.extend(await self.parse_post(session, link, title))

            next_page = soup.select_one('div[id="next_page"] a')
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    results.extend(await self.parse_profile(session, URL(next_page)))
            return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []

    async def parse_post(self, session: Session, url: URL, title=None):
        try:
            await log("Scraping post: " + str(url), quiet=self.quiet)
            soup = await session.get_BS4(url)
            results = []

            content_section = soup.select_one('div[class="flex justify-between items-center"]')

            images = content_section.select("img")
            for image in images:
                download_link = URL(image.get('src'))
                results.append([title, download_link, url])

            videos = content_section.select("source")
            for video in videos:
                download_link = URL(video.get('src'))
                results.append([title, download_link, url])

            return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []