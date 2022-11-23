from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class HGameCGCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), quiet=self.quiet)
        results = await self.get_album(session, url)
        for result in results:
            await domain_obj.add_to_album(result['title'], result['url'], result['referral'])
        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return domain_obj

    async def get_album(self, session: Session, url: URL):
        results = []
        try:
            soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("div[class=navbar] h1").get_text())
            results = []

            images = soup.select("div[class=image] a")
            for image in images:
                image = image.get('href')
                image = URL("https://" + url.host + image)
                link = await self.get_image(session, image)
                results.append({'url': link, 'title': title, 'referral': url, 'cookies': ''})

            next_page = soup.find("a", text="Next Page")
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL("https://" + url.host + next_page)
                    results.extend(result for result in await self.get_album(session, next_page))

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        return results

    async def get_image(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            image = soup.select_one("div[class=hgamecgimage] img")
            image = URL(image.get('src'))
            return image
        except:
            logger.error(f"Unable to get image from {str(url)}")
