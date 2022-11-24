import asyncio
from typing import Dict

from .scraper_helper import ScrapeMapper
from ..base_functions.base_functions import log
from ..base_functions.data_classes import AuthData, SkipData
from ..client.client import Client


async def scrape(urls, client: Client, file_args: Dict, jdownloader_args: Dict, runtime_args: Dict,
                 jdownloader_auth: AuthData, simpcity_auth: AuthData, socialmediagirls_auth: AuthData,
                 xbunker_auth: AuthData, skip_data: SkipData, quiet=False):
    await log("Starting Scrape", quiet=quiet)

    scraper = ScrapeMapper(client=client, file_args=file_args, jdownloader_args=jdownloader_args,
                           runtime_args=runtime_args, xbunker_auth=xbunker_auth,
                           socialmediagirls_auth=socialmediagirls_auth, simpcity_auth=simpcity_auth,
                           jdownloader_auth=jdownloader_auth, skip_data=skip_data, quiet=quiet)
    tasks = []
    for link in urls:
        tasks.append(scraper.map_url(link))
    await asyncio.gather(*tasks)

    await scraper.close()

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    return Cascade
