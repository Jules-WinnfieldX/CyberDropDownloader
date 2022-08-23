import asyncio

from .scraper_helper import ScrapeMapper
from ..base_functions.base_functions import log
from ..base_functions.data_classes import AuthData, SkipData
from ..client.client import Client


async def scrape(urls, client: Client, include_id: bool, leakednudes_auth: AuthData, socialmediagirls_auth: AuthData,
                 thotsbay_auth: AuthData, separate_posts: bool, skip_data: SkipData):
    await log("Starting Scrape")

    scraper = ScrapeMapper(client=client, include_id=include_id, leakednudes_auth=leakednudes_auth,
                           socialmediagirls_auth=socialmediagirls_auth, thotsbay_auth=thotsbay_auth,
                           separate_posts=separate_posts, skip_data=skip_data)
    tasks = []
    for link in urls:
        tasks.append(scraper.map_url(link))
    await asyncio.gather(*tasks)

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    return Cascade
