from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions import logger, ssl_context


class GfycatCrawler():
    def __init__(self, *, scraping_mapper, session):
        self.scraping_mapper = scraping_mapper
        self.session = session
        self.lock = 0

    async def fetch(self, session, url):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                video = soup.select_one("video[class='video media']")
                video_srcs = video.select("source")

                # Find the biggest video source, usually the host is giant.gyfcat
                video_link = None
                for src in video_srcs:
                    link = URL(src.get("src"))
                    if str(link.host).find("giant") != -1:
                        video_link = link
                if video_link is None:
                    video_link = URL(video_srcs[0].get("src"))

                return video_link

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
