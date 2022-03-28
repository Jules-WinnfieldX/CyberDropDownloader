import asyncio

import aiohttp
import tldextract

from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.Chibisafe_Spider import ChibisafeCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .data_classes import *
from .base_functions import *


async def scrape(urls, include_id: bool):
    Cascade = CascadeItem({})

    ShareX_urls = []
    Chibisafe_urls = []
    Erome_urls = []
    GoFile_urls = []
    unsupported_urls = []

    log("Starting Scrape", Fore.WHITE)

    for url in urls:
        url = url.replace('\n', '')
        url_extract = tldextract.extract(url)
        base_domain = "{}.{}".format(url_extract.domain, url_extract.suffix)

        if base_domain in mapping_ShareX:
            if check_direct(url):
                Cascade.add_to_album(base_domain, "ShareX Loose Files", url, url)
            else:
                ShareX_urls.append(url)

        elif base_domain in mapping_Chibisafe:
            if check_direct(url):
                if 'bunkr' in url:
                    Cascade.add_to_album(base_domain, "Chibisafe Loose Files", bunkr_parse(url), url)
                else:
                    Cascade.add_to_album(base_domain, "Chibisafe Loose Files", url, url)
            else:
                Chibisafe_urls.append(url)

        elif base_domain in mapping_Erome:
            Erome_urls.append(url)

        elif base_domain in mapping_GoFile:
            GoFile_urls.append(url)

        elif base_domain in mapping_Pixeldrain:
            title = url.split('/')[-1]
            Cascade.add_to_album(base_domain, title, pixeldrain_parse(url, title), url)

        # TODO entire thotsbay forum pages, scrape all images, embedded videos, scrape all links

        else:
            unsupported_urls.append(url)

    erome_crawler = EromeCrawler(include_id=include_id)
    sharex_crawler = ShareXCrawler(include_id=include_id)
    chibisafe_crawler = ChibisafeCrawler(include_id=include_id)
    gofile_crawler = GofileCrawler()

    tasks = []
    headers = {"user-agent": user_agent}
    async with aiohttp.ClientSession(headers=headers, raise_for_status=True) as session:
        for url in Erome_urls:
            tasks.append(erome_crawler.fetch(session, url))
        for url in ShareX_urls:
            tasks.append(sharex_crawler.fetch(session, url))
        for url in Chibisafe_urls:
            tasks.append(chibisafe_crawler.fetch(session, url))
        for url in GoFile_urls:
            tasks.append(gofile_crawler.fetch(url))
        results = await asyncio.gather(*tasks)

    for item_pair in results:
        domain_item, cookie_item = item_pair
        Cascade.add_albums(domain_item)
        Cascade.add_cookie(cookie_item)

    return Cascade
