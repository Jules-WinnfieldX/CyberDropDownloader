from yarl import URL

from ..base_functions.base_functions import log, logger
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class AnonfilesCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), quiet=self.quiet)

        try:
            soup = await session.get_BS4(url)

            title = "Anon Loose Files"
            link = soup.select_one("a[id=download-url]")
            link = URL(link.get('href'))
            await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj
