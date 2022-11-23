from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class CyberdropCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        if await check_direct(url):
            link = URL(url)
            await domain_obj.add_to_album(link=link, referral=url, title="Cyberdrop Loose Files")
            return domain_obj

        await log("Starting scrape of " + str(url), quiet=self.quiet)

        try:
            soup = await session.get_BS4(url)

            title = soup.select_one("h1[id=title]").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                titlep2 = [s for s in titlep2 if "." in s][-1]
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())

            links = soup.select('div[class="image-container column"] a')
            for link in links:
                link = URL(link.get('href'))
                if 'cyberdrop' in link.host:
                    link = URL('https://fs-01.cyberdrop.cc').with_name(link.name)
                await domain_obj.add_to_album(title, link, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj
