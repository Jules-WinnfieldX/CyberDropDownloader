from __future__ import annotations

import asyncio
from pathlib import Path

from yarl import URL

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

        self.existing_crawlers = {}
        self.existing_crawler_tasks = {}
        self.mapping = {}

    async def bunkr(self, scrape_item: ScrapeItem):
        if not self.existing_crawlers.get("bunkr"):
            from cyberdrop_dl.scraper.crawlers.bunkr_crawler import BunkrCrawler
            self.existing_crawlers["bunkr"] = BunkrCrawler(self.manager)
            await self.existing_crawlers["bunkr"].startup()
            self.existing_crawler_tasks["bunkr"] = asyncio.create_task(self.existing_crawlers["bunkr"].run_loop())
        await self.existing_crawlers["bunkr"].add_to_queue(scrape_item)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def close(self):
        for task in self.existing_crawler_tasks.values():
            task.cancel()

    async def map_url(self, url_to_map: URL, parent_title: str = ""):
        scrape_item = ScrapeItem(url_to_map, parent_title)

        if not url_to_map:
            return
        if not url_to_map.host:
            return

        key = next((key for key in self.mapping if key in url_to_map.host), None)
        if key:
            handler = self.mapping[key]
            await handler(scrape_item=scrape_item)
            return
