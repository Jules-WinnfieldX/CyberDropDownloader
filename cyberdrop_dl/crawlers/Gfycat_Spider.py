from yarl import URL

from ..base_functions.base_functions import log, logger
from ..client.client import Session


class GfycatCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)

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
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
