import asyncio

import aiofiles
from yarl import URL

from .crawlers.Anonfiles_Spider import AnonfilesCrawler
from .crawlers.Chibisafe_Spider import ChibisafeCrawler
from .crawlers.Coomer_Spider import CoomerCrawler
from .crawlers.Cyberfile_Spider import CyberfileCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.Gfycat_Spider import GfycatCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .crawlers.Pixeldrain_Crawler import PixelDrainCrawler
from .crawlers.Redgifs_Spider import RedGifsCrawler
from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Thotsbay_Spider import ThotsbayCrawler
from .base_functions import log
from .data_classes import CascadeItem


class ScrapeMapper():
    def __init__(self, *, session, include_id=False, thotsbay_auth=None, separate_posts=False):
        self.include_id = include_id
        self.separate_posts = separate_posts
        self.thotsbay_auth = thotsbay_auth
        self.session = session
        self.Cascade = CascadeItem({})

        self.anonfiles_crawler = None
        self.chibisafe_crawler = None
        self.coomer_crawler = None
        self.cyberfile_crawler = None
        self.erome_crawler = None
        self.gfycat_crawler = None
        self.gofile_crawler = None
        self.pixeldrain_crawler = None
        self.redgifs_crawler = None
        self.sharex_crawler = None
        self.thotsbay_crawler = None

        self.semaphore = asyncio.Semaphore(1)
        self.mapping = {"anonfiles.com": self.Anonfiles, "bunkr.is": self.Chibisafe,
                        "bunkr.to": self.Chibisafe, "coomer.party": self.coomer,
                        "cyberdrop.cc": self.Chibisafe, "cyberdrop.me": self.Chibisafe,
                        "cyberdrop.nl": self.Chibisafe, "cyberdrop.to": self.Chibisafe,
                        "cyberfile.is": self.cyberfile, "erome.com": self.Erome,
                        "gfycat.com": self.gfycat, "gofile.io": self.GoFile,
                        "jpg.church": self.ShareX, "pixeldrain.com": self.Pixeldrain,
                        "pixl.is": self.ShareX, "putme.ga": self.ShareX,
                        "putmega.com": self.ShareX, "redgifs.com": self.redgifs,
                        "socialmediagirls.com": self.ThotsBay, "thotsbay.com": self.ThotsBay}

    async def Anonfiles(self, url: URL, title=None):
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(
                include_id=self.include_id)
        domain_obj = await self.anonfiles_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Chibisafe(self, url: URL, title=None):
        if not self.chibisafe_crawler:
            self.chibisafe_crawler = ChibisafeCrawler(
                include_id=self.include_id)
        domain_obj = await self.chibisafe_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def coomer(self, url: URL, title=None):
        if not self.coomer_crawler:
            self.coomer_crawler = CoomerCrawler(include_id=self.include_id)
        domain_obj = await self.coomer_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def cyberfile(self, url: URL, title=None):
        if not self.cyberfile_crawler:
            self.cyberfile_crawler = CyberfileCrawler()
        async with self.semaphore:
            domain_obj = await self.cyberfile_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Erome(self, url: URL, title=None):
        if not self.erome_crawler:
            self.erome_crawler = EromeCrawler(include_id=self.include_id)
        domain_obj = await self.erome_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def GoFile(self, url: URL, title=None):
        if not self.gofile_crawler:
            try:
                self.gofile_crawler = GofileCrawler()
            except:
                await log("Couldn't start the GoFile crawler")
                return
        domain_obj = await self.gofile_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def gfycat(self, url: URL, title=None):
        if not self.gfycat_crawler:
            self.gfycat_crawler = GfycatCrawler(
                scraping_mapper=self, session=self.session)
        content_url = await self.gfycat_crawler.fetch(self.session, url)
        if content_url:
            if title:
                await self.Cascade.add_to_album("gfycat.com", f"{title}/gifs", content_url, url)
            else:
                await self.Cascade.add_to_album("gfycat.com", "gifs", content_url, url)

    async def Pixeldrain(self, url: URL, title=None):
        if not self.pixeldrain_crawler:
            self.pixeldrain_crawler = PixelDrainCrawler()
        domain_obj = await self.pixeldrain_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def redgifs(self, url: URL, title=None):
        if not self.redgifs_crawler:
            self.redgifs_crawler = RedGifsCrawler(scraping_mapper=self, session=self.session)
        content_url = await self.redgifs_crawler.fetch(self.session, url)
        if content_url:
            if title:
                await self.Cascade.add_to_album("redgifs.com", f"{title}/gifs", content_url, url)
            else:
                await self.Cascade.add_to_album("redgifs.com", "gifs", content_url, url)

    async def ShareX(self, url: URL, title=None):
        if not self.sharex_crawler:
            self.sharex_crawler = ShareXCrawler(include_id=self.include_id)
        domain_obj = await self.sharex_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def ThotsBay(self, url: URL, title=None):
        if not self.thotsbay_crawler:
            self.thotsbay_crawler = ThotsbayCrawler(
                include_id=self.include_id, auth=self.thotsbay_auth,
                scraping_mapper=self, session=self.session, separate_posts=self.separate_posts)
        await self.Cascade.extend(await self.thotsbay_crawler.fetch(self.session, url))

    async def map_url(self, url_to_map: URL, title=None):
        for key, value in self.mapping.items():
            if key in url_to_map.host:
                await value(url=url_to_map, title=title)
                return
        await log(str(url_to_map) + " is not supported currently.")
        async with aiofiles.open("./Unsupported_Urls.txt", mode='a') as f:
            await f.write(str(url_to_map)+"\n")
