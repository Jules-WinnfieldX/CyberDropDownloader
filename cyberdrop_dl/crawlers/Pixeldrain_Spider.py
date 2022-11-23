from yarl import URL

from ..base_functions.base_functions import log, logger
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class PixelDrainCrawler:
    def __init__(self, quiet: bool):
        self.quiet = quiet
        self.api = URL('https://pixeldrain.com/api/')

    async def fetch(self, session: Session, url: URL):
        await log("Starting scrape of " + str(url), quiet=self.quiet)
        domain_obj = DomainItem("pixeldrain.com", {})

        identifier = str(url).split('/')[-1]
        if url.parts[1] == 'l':
            links = await self.get_listings(session, identifier, url)
            if links:
                for link in links:
                    await domain_obj.add_to_album(identifier, link, url)
        else:
            link = await self.create_download_link(identifier)
            await domain_obj.add_to_album("Loose Pixeldrain Files", link, url)

        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return domain_obj

    async def get_listings(self, session: Session, identifier: str, url: URL):
        links = []
        try:
            content = await session.get_json((self.api / "list" / identifier))
            for file in content['files']:
                links.append(await self.create_download_link(file['id']))
            return links
        except Exception as e:
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return None

    async def create_download_link(self, file):
        final_url = (URL('https://pixeldrain.com/api/file/') / file).with_query('download')
        return final_url
