import asyncio

from .scraper_helper import ScrapeMapper
from ..base_functions.base_functions import log
from ..base_functions.data_classes import AuthData, SkipData
from ..client.client import Client


async def scrape(urls, client: Client, include_id: bool, jdownloader_enable: bool, jdownloader_device: str, xbunker_auth: AuthData,
                 socialmediagirls_auth: AuthData, simpcity_auth: AuthData, jdownloader_auth: AuthData,
                 separate_posts: bool, skip_data: SkipData, output_last: list):
    await log("Starting Scrape")

    scraper = ScrapeMapper(client=client, include_id=include_id, jdownloader_enable=jdownloader_enable,
                           jdownloader_device=jdownloader_device, xbunker_auth=xbunker_auth,
                           socialmediagirls_auth=socialmediagirls_auth, simpcity_auth=simpcity_auth,
                           jdownloader_auth=jdownloader_auth, separate_posts=separate_posts, skip_data=skip_data,
                           output_last=output_last)
    tasks = []
    for link in urls:
        tasks.append(scraper.map_url(link))
    await asyncio.gather(*tasks)

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    return Cascade
