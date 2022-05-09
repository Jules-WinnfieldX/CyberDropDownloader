import asyncio

import aiohttp
from colorama import Fore

from .base_functions import log, user_agent
from .data_classes import AuthData
from .scraper_helper import ScrapeMapper


async def scrape(urls, include_id: bool, thotsbay_auth: AuthData, separate_posts: bool):
    await log("Starting Scrape", Fore.WHITE)
    headers = {"user-agent": user_agent}
    jar = aiohttp.CookieJar(quote_cookie=False)

    async with aiohttp.ClientSession(headers=headers, raise_for_status=True, cookie_jar=jar) as session:
        scraper = ScrapeMapper(session=session, include_id=include_id, thotsbay_auth=thotsbay_auth,
                               separate_posts=separate_posts)
        tasks = []
        for link in urls:
            tasks.append(scraper.map_url(link))
        await asyncio.gather(*tasks)

    Cascade = scraper.Cascade
    Cascade.cookies = jar
    await Cascade.dedupe()
    return Cascade
