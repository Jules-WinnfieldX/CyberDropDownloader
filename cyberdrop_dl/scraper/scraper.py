from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import aiofiles
from yarl import URL

from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import log\

if TYPE_CHECKING:
    from typing import List

    from cyberdrop_dl.managers.manager import Manager


class ScrapeMapper:
    """This class maps links to their respective handlers, or JDownloader if they are unsupported"""
    def __init__(self, manager: Manager):
        self.mapping = {"bunkr": self.bunkr, "cyberdrop": self.cyberdrop}
        self.manager = manager

        self.complete = False

        self.existing_crawlers = {}

    async def bunkr(self, scrape_item: ScrapeItem) -> None:
        """Adds a bunkr link to the bunkr crawler"""
        if not self.existing_crawlers.get("bunkr"):
            from cyberdrop_dl.scraper.crawlers.bunkr_crawler import BunkrCrawler
            self.existing_crawlers['bunkr'] = BunkrCrawler(self.manager)
            await self.existing_crawlers['bunkr'].startup()
            await self.manager.download_manager.get_download_instance("bunkr", 1)
            asyncio.create_task(self.existing_crawlers['bunkr'].run_loop())
        await self.existing_crawlers['bunkr'].scraper_queue.put(scrape_item)
        await asyncio.sleep(0)

    async def cyberdrop(self, scrape_item: ScrapeItem) -> None:
        """Adds a cyberdrop link to the cyberdrop crawler"""
        if not self.existing_crawlers.get("cyberdrop"):
            from cyberdrop_dl.scraper.crawlers.cyberdrop_crawler import CyberdropCrawler
            self.existing_crawlers['cyberdrop'] = CyberdropCrawler(self.manager)
            await self.existing_crawlers['cyberdrop'].startup()
            await self.manager.download_manager.get_download_instance("cyberdrop", self.manager.client_manager.simultaneous_per_domain)
            asyncio.create_task(self.existing_crawlers['cyberdrop'].run_loop())
        await self.existing_crawlers['cyberdrop'].scraper_queue.put(scrape_item)
        await asyncio.sleep(0)

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
                handler = self.mapping[key]
                await handler(scrape_item=scrape_item)
                continue

            if self.complete:
                break
