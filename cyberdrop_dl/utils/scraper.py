import asyncio

import aiohttp
from colorama import Fore

from .base_functions import log, url_sort, user_agent
from .crawlers.Anonfiles_Spider import AnonfilesCrawler
from .crawlers.Chibisafe_Spider import ChibisafeCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Thotsbay_Spider import ThotsbayCrawler
from .data_classes import CascadeItem


async def scrape(urls, include_id: bool, thotsbay_username: str, thotsbay_password: str):
    Cascade = CascadeItem({})

    await log("Starting Scrape", Fore.WHITE)

    ShareX_urls, Chibisafe_urls, Erome_urls, GoFile_urls, Thotsbay_urls, Anonfile_urls = await url_sort(urls, Cascade)

    erome_crawler = EromeCrawler(include_id=include_id)
    sharex_crawler = ShareXCrawler(include_id=include_id)
    chibisafe_crawler = ChibisafeCrawler(include_id=include_id)
    gofile_crawler = GofileCrawler()
    anonfiles_crawler = AnonfilesCrawler(include_id=include_id)
    thotsbay_crawler = ThotsbayCrawler(include_id=include_id, username=thotsbay_username, password=thotsbay_password,
                                       erome_crawler=erome_crawler, sharex_crawler=sharex_crawler,
                                       chibisafe_crawler=chibisafe_crawler, gofile_crawler=gofile_crawler,
                                       anonfiles_crawler=anonfiles_crawler)

    tasks = []
    headers = {"user-agent": user_agent}
    jar = aiohttp.CookieJar(quote_cookie=False)

    async with aiohttp.ClientSession(headers=headers, raise_for_status=True, cookie_jar=jar) as session:
        # Returns Domain items
        for url in Erome_urls:
            tasks.append(erome_crawler.fetch(session, url))
        for url in ShareX_urls:
            tasks.append(sharex_crawler.fetch(session, url))
        for url in Chibisafe_urls:
            tasks.append(chibisafe_crawler.fetch(session, url))
        for url in GoFile_urls:
            tasks.append(gofile_crawler.fetch(session, url))
        for url in Anonfile_urls:
            tasks.append(anonfiles_crawler.fetch(session, url))
        results = await asyncio.gather(*tasks)

        for domain_item in results:
            await Cascade.add_albums(domain_item)

        # Returns a Cascade item
        results = []
        for url in Thotsbay_urls:
            results.append(await thotsbay_crawler.fetch(session, url))

        for result in results:
            if result:
                if result.domains:
                    await Cascade.extend(result)

    Cascade.cookies = jar
    await Cascade.dedupe()
    return Cascade
