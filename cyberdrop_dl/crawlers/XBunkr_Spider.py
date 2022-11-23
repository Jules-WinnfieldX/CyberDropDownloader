from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class XBunkrCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        if "media" in url.host:
            await domain_obj.add_to_album("Loose XBunkr Files", url, url)
            return domain_obj

        try:
            soup = await session.get_BS4(url)
            links = soup.select("a[class=image]")
            title = await make_title_safe(soup.select_one("h1[id=title]").text)
            title = title.strip()
            for link in links:
                link = URL(link.get('href'))
                await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj
