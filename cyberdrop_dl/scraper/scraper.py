from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem


class ScrapeMapper:
    """This class maps links to their respective handlers, or JDownloader if they are unsupported"""
    def __init__(self, manager: Manager):
        # self.mapping = {"anonfiles": self.Anonfiles, "bayfiles": self.Anonfiles, "xbunkr": self.XBunkr,
        #                 "bunkr": self.Bunkr, "cyberdrop": self.Cyberdrop, "cyberfile": self.CyberFile,
        #                 "erome": self.Erome, "fapello": self.Fapello, "gfycat": self.Gfycat, "gofile": self.GoFile,
        #                 "hgamecg": self.HGameCG, "imgbox": self.ImgBox, "pixeldrain": self.PixelDrain,
        #                 "postimg": self.PostImg, "saint": self.Saint, "img.kiwi": self.ShareX, "imgur": self.Imgur,
        #                 "jpg.church": self.ShareX, "jpg.fish": self.ShareX, "jpg.pet": self.ShareX,
        #                 "jpg1.su": self.ShareX, "jpeg.pet": self.ShareX, "pixl.li": self.ShareX,
        #                 "nsfw.xxx": self.NSFW_XXX, "pimpandhost": self.PimpAndHost, "lovefap": self.LoveFap,
        #                 "e-hentai": self.EHentai, "gallery.deltaporno": self.ShareX,
        #                 "coomer.party": self.Coomeno, "coomer.su": self.Coomeno, "kemono.party": self.Coomeno,
        #                 "kemono.su": self.Coomeno, "nudostar": self.Xenforo, "simpcity": self.Xenforo,
        #                 "socialmediagirls": self.Xenforo, "xbunker": self.Xenforo, "reddit": self.Reddit,
        #                 "redd.it": self.Reddit, "redgifs": self.RedGifs}
        self.manager = manager

        self.complete = False

        self.existing_crawlers = {}
        self.existing_crawler_tasks = {}
        self.mapping = {}

    async def bunkr(self, scrape_item: ScrapeItem):
        if not self.existing_crawlers.get("bunkr"):
            from cyberdrop_dl.scraper.crawlers.bunkr_crawler import BunkrCrawler
            self.existing_crawlers["bunkr"] = BunkrCrawler(self.manager)
            await self.existing_crawlers["bunkr"].startup()
            # TODO create class for manager to keep track of domain limits / rate limits
            await self.manager.download_manager.get_download_instance("bunkr", 2)
        await self.existing_crawlers["bunkr"].add_to_queue(scrape_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_complete(self):
        if self.manager.queue_manager.url_objects_to_map.empty():
            for crawler in self.existing_crawlers.values():
                if not crawler.complete:
                    return False
            return True

    async def map_urls(self):
        while True:
            scrape_item: ScrapeItem = await self.manager.queue_manager.url_objects_to_map.get()

            if not scrape_item.url:
                continue
            if not scrape_item.url.host:
                continue

            key = next((key for key in self.mapping if key in scrape_item.url.host), None)
            if key:
                handler = self.mapping[key]
                await handler(scrape_item=scrape_item)
                continue

            if self.complete:
                break
