from typing import Dict

from yarl import URL

from ..base_functions.base_functions import log, logger, check_direct
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class ImgBoxCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})
        await log("Starting scrape of " + str(url), quiet=self.quiet)

        if await check_direct(url):
            await domain_obj.add_to_album(link=URL(url), referral=url, title="ImgBox Loose Files")
            return domain_obj

        try:
            if "g" in url.parts:
                images = await self.folder(session, url)
                for img in images:
                    await domain_obj.add_to_album(url.raw_name, img, url)
            else:
                img = await self.singular(session, url)
                await domain_obj.add_to_album("Loose ImgBox Files", img, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def folder(self, session: Session, url: URL):
        soup = await session.get_BS4(url)
        output = []
        
        images = soup.find('div', attrs={'id': 'gallery-view-content'})
        for link in images.findAll("img"):
            output.append(URL(link.get('src').replace("thumbs", "images").replace("_b", "_o")))

        return output

    async def singular(self, session: Session, url: URL):
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("img[id=img]").get('src'))
        return link
