import asyncio

from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.Chibisafe_Spider import ChibisafeCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .crawlers.Thotsbay_Spider import ThotsbayCrawler
from .data_classes import *
from .base_functions import *


async def scrape(urls, include_id: bool, thotsbay_username: str, thotsbay_password: str):
    Cascade = CascadeItem({})

    log("Starting Scrape", Fore.WHITE)

    ShareX_urls, Chibisafe_urls, Erome_urls, GoFile_urls, Thotsbay_urls = url_sort(urls, Cascade)

    erome_crawler = EromeCrawler(include_id=include_id)
    sharex_crawler = ShareXCrawler(include_id=include_id)
    chibisafe_crawler = ChibisafeCrawler(include_id=include_id)
    gofile_crawler = GofileCrawler()
    thotsbay_crawler = ThotsbayCrawler(include_id=include_id, username=thotsbay_username, password=thotsbay_password,
                                       erome_crawler=erome_crawler, sharex_crawler=sharex_crawler,
                                       chibisafe_crawler=chibisafe_crawler, gofile_crawler=gofile_crawler)

    tasks = []
    headers = {"user-agent": user_agent}
    jar = aiohttp.CookieJar(quote_cookie=False)

    # Returns Domain items
    async with aiohttp.ClientSession(headers=headers, raise_for_status=True, cookie_jar=jar) as session:
        for url in Erome_urls:
            tasks.append(erome_crawler.fetch(session, url))
        for url in ShareX_urls:
            tasks.append(sharex_crawler.fetch(session, url))
        for url in Chibisafe_urls:
            tasks.append(chibisafe_crawler.fetch(session, url))
        for url in GoFile_urls:
            tasks.append(gofile_crawler.fetch(session, url))
        results = await asyncio.gather(*tasks)

    for domain_item in results:
        Cascade.add_albums(domain_item)

    # Returns a Cascade item
    async with aiohttp.ClientSession(headers=headers, raise_for_status=True, cookie_jar=jar) as session:
        for url in Thotsbay_urls:
            tasks.append(thotsbay_crawler.fetch(session, url))
        results = await asyncio.gather(*tasks)

    for result in results:
        Cascade.extend(result)

    Cascade.cookies = jar

    return Cascade
