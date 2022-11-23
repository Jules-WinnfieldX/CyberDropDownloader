from typing import Dict

from yarl import URL

from ..base_functions.base_functions import log, logger
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class PostImgCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})
        await log("Starting scrape of " + str(url), quiet=self.quiet)

        try:
            if "gallery" in url.parts:
                listed = await self.folder(session, url)
                for referer, img in listed.items():
                    await domain_obj.add_to_album(url.raw_name, img, referer)
            else:
                img = await self.singular(session, url)
                await domain_obj.add_to_album("Loose PostIMG Files", img, url)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def folder(self, session: Session, url: URL):
        album = url.raw_name
        data = {"action": "list", "album": album}
        output = {}
        i = 1
        while True:
            data_used = data
            data_used["page"] = i
            data_out = await session.post(URL("https://postimg.cc/json"), data_used)
            if data_out['status_code'] != 200 or not data_out['images']:
                break
            for item in data_out['images']:
                output[URL("https://postimg.cc/" + item[0])] = URL(item[4].replace(item[0], item[1]))
            i += 1
        return output

    async def singular(self, session: Session, url: URL):
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("a[id=download]").get('href').replace("?dl=1", ""))
        return link
