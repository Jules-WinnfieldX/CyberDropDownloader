from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log, logger
from ..client.client import Session


class RedGifsCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
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
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
