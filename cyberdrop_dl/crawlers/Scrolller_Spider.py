from __future__ import annotations

from typing import TYPE_CHECKING, Dict
import json

from yarl import URL

from ..base_functions.base_functions import log, logger, create_media_item
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession

class ScrolllerCrawler:
    def __init__(self, separate_posts: bool, quiet: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter,
                 args: Dict[str, str]):
        self.separate_posts = separate_posts
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.error_writer = error_writer
        self.scrolller_api = URL("https://api.scrolller.com/api/v2/graphql")
        self.headers = {"Content-Type": "application/json"}

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        subreddit = url.parts[-1]
        domain_obj = DomainItem("scrolller", {})
        try:
            log(f"Starting: {subreddit}", quiet=self.quiet, style="green")

            body = {
                "query": """
                    query SubredditQuery(
                        $url: String!
                        $filter: SubredditPostFilter
                        $iterator: String
                    ) {
                        getSubreddit(url: $url) {
                            title
                            children(
                                limit: 10000
                                iterator: $iterator
                                filter: $filter
                                disabledHosts: null
                            ) {
                                iterator
                                items {
                                    title
                                    mediaSources {
                                        url
                                    }
                                    blurredMediaSources {
                                        url
                                    }
                                }
                            }
                        }
                    }
                """,
                "variables": {
                    "url": f"/r/{subreddit}",
                    "filter": None,
                    "hostsDown": None
                },
            }

            iterator = None
            prev_iterator = None
            iterations = 0

            while True:
                # Fetching items with iterator iterator
                body["variables"]["iterator"] = iterator
                response = await session.post(self.scrolller_api, data=json.dumps(body))

                if response:
                    data = response
                    items = data["data"]["getSubreddit"]["children"]["items"]

                    for item in items:
                        title = str(url.parts[-1]).split(".")[0]
                        mediaSources = item['mediaSources']
                        if mediaSources:
                            highest_res_image_url = mediaSources[-1]['url']
                            # Fetching highest resolution image
                            await self.get_image(URL(highest_res_image_url), URL(highest_res_image_url), title, domain_obj)

                    prev_iterator = iterator
                    iterator = data["data"]["getSubreddit"]["children"]["iterator"]

                    # If there's no more items or the iterator hasn't changed, break the loop
                    if not items or iterator == prev_iterator:
                        break
                    if iterations > 0 and iterator is None:
                        break
                else:
                    break

                iterations += 1

            await self.SQL_Helper.insert_domain("scrolller", url, domain_obj)
            log(f"Finished: {subreddit}", quiet=self.quiet, style="green")
        except Exception as e:
            logger.debug("Error encountered while handling %s", subreddit, exc_info=True)
            await self.error_writer.write_errored_scrape(subreddit, e, self.quiet)

        return domain_obj

    async def get_image(self, url: URL, referer: URL, title: str, domain_obj: DomainItem):
        try:
            media_item = await create_media_item(url, referer, self.SQL_Helper, "scrolller")
        except NoExtensionFailure:
            logger.debug("Couldn't get extension for %s", url)
            return
        await domain_obj.add_media(title, media_item)
