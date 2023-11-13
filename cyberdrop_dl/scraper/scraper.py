from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import aiofiles
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import log

if TYPE_CHECKING:
    from typing import List

    from cyberdrop_dl.managers.manager import Manager


class ScrapeMapper:
    """This class maps links to their respective handlers, or JDownloader if they are unsupported"""
    def __init__(self, manager: Manager):
        self.mapping = {"bunkr": self.bunkr, "coomer": self.coomer, "cyberdrop": self.cyberdrop,
                        "cyberfile": self.cyberfile, "e-hentai": self.ehentai, "erome": self.erome,
                        "fapello": self.fapello, "kemono": self.kemono, "saint": self.saint}
        self.existing_crawlers = {}
        self.manager = manager

        self.complete = False

    async def bunkr(self) -> None:
        """Creates a Bunkr Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.bunkr_crawler import BunkrCrawler
        self.existing_crawlers['bunkr'] = BunkrCrawler(self.manager)

    async def coomer(self) -> None:
        """Creates a Coomer Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.coomer_crawler import CoomerCrawler
        self.existing_crawlers['coomer'] = CoomerCrawler(self.manager)

    async def cyberdrop(self) -> None:
        """Creates a Cyberdrop Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.cyberdrop_crawler import CyberdropCrawler
        self.existing_crawlers['cyberdrop'] = CyberdropCrawler(self.manager)

    async def cyberfile(self) -> None:
        """Creates a Cyberfile Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.cyberfile_crawler import CyberfileCrawler
        self.existing_crawlers['cyberfile'] = CyberfileCrawler(self.manager)

    async def ehentai(self) -> None:
        """Creates a EHentai Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.ehentai_crawler import EHentaiCrawler
        self.existing_crawlers['e-hentai'] = EHentaiCrawler(self.manager)

    async def erome(self) -> None:
        """Creates a Erome Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.erome_crawler import EromeCrawler
        self.existing_crawlers['erome'] = EromeCrawler(self.manager)

    async def fapello(self) -> None:
        """Creates a Fappelo Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.fapello_crawler import FapelloCrawler
        self.existing_crawlers['fapello'] = FapelloCrawler(self.manager)

    async def kemono(self) -> None:
        """Creates a Kemono Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.kemono_crawler import KemonoCrawler
        self.existing_crawlers['kemono'] = KemonoCrawler(self.manager)

    async def saint(self) -> None:
        """Creates a Saint Crawler instance"""
        from cyberdrop_dl.scraper.crawlers.saint_crawler import SaintCrawler
        self.existing_crawlers['saint'] = SaintCrawler(self.manager)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def regex_links(self, line: str) -> List:
        """Regex grab the links from the URLs.txt file
        This allows code blocks or full paragraphs to be copy and pasted into the URLs.txt"""
        yarl_links = []
        if line.lstrip().rstrip().startswith('#'):
            return yarl_links

        all_links = [x.group().replace(".md.", ".") for x in re.finditer(
            r"(?:http.*?)(?=($|\n|\r\n|\r|\s|\"|\[/URL]|']\[|]\[|\[/img]))", line)]
        for link in all_links:
            yarl_links.append(URL(link))
        return yarl_links

    async def load_links(self) -> None:
        """Loads links from args / input file"""
        links = []
        async with aiofiles.open(self.manager.file_manager.input_file, "r", encoding="utf8") as f:
            async for line in f:
                assert isinstance(line, str)
                links.extend(await self.regex_links(line))
        links.extend(self.manager.args_manager.other_links)
        links = list(filter(None, links))

        if not links:
            await log("No valid links found.")
        for link in links:
            item = ScrapeItem(url=link, parent_title="")
            await self.manager.queue_manager.url_objects_to_map.put(item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_complete(self) -> bool:
        if self.manager.queue_manager.url_objects_to_map.empty():
            for crawler in self.existing_crawlers.values():
                if not crawler.complete:
                    return False
            return True
        return False

    async def map_urls(self) -> None:
        """Maps URLs to their respective handlers"""
        while True:
            self.complete = False
            scrape_item: ScrapeItem = await self.manager.queue_manager.url_objects_to_map.get()

            if not scrape_item.url:
                continue
            if not scrape_item.url.host:
                continue

            key = next((key for key in self.mapping if key in scrape_item.url.host.lower()), None)
            if key:
                """If the crawler doesn't exist, create it, finally add the scrape item to it's queue"""
                if not self.existing_crawlers.get(key):
                    start_handler = self.mapping[key]
                    await start_handler()
                    await self.existing_crawlers[key].startup()
                    await self.manager.download_manager.get_download_instance(key)
                    asyncio.create_task(self.existing_crawlers[key].run_loop())
                await self.existing_crawlers[key].scraper_queue.put(scrape_item)
                await asyncio.sleep(0)
                continue

            if self.complete:
                break
