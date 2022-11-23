from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class EromeCrawler():
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), quiet=self.quiet)

        try:
            soup = await session.get_BS4(url)
            title = soup.select_one('div[class="col-sm-12 page-content"] h1').get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            # Images
            for link in soup.select('img[class="img-front lasyload"]'):
                await domain_obj.add_to_album(title, URL(link['data-src']), url)

            # Videos
            for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                await domain_obj.add_to_album(title, URL(link['src']), url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj
