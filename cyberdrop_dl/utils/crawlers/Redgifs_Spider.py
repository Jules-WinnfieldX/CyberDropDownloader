from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions import log, logger, ssl_context


class RedGifsCrawler():
    def __init__(self, *, scraping_mapper, session):
        self.scraping_mapper = scraping_mapper
        self.session = session
        self.lock = 0

    async def fetch(self, session, url):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                video_metas = soup.select("meta[property='og:video']")

                # Find the video that doesn't contain "mobile"
                video_src = None
                for video_meta in video_metas:
                    link = video_meta.get("content")
                    if "mobile" not in link:
                        video_src = URL(link)

                # Just get the first one if we didn't find the non-mobile
                if video_src is None and len(video_metas) != 0:
                    video_src = URL(video_metas[0].get("content"))

                return video_src

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
