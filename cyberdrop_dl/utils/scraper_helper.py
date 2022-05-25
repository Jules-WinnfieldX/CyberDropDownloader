import asyncio

import aiofiles
from yarl import URL

from .crawlers.Anonfiles_Spider import AnonfilesCrawler
from .crawlers.Bunkr_Spider import BunkrCrawler
from .crawlers.Coomer_Spider import CoomerCrawler
from .crawlers.Cyberdrop_Spider import CyberdropCrawler
from .crawlers.Cyberfile_Spider import CyberfileCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.Gfycat_Spider import GfycatCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .crawlers.Kemono_Spider import KemonoCrawler
from .crawlers.Pixeldrain_Crawler import PixelDrainCrawler
from .crawlers.Redgifs_Spider import RedGifsCrawler
from .crawlers.Saint_Spider import SaintCrawler
from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Thotsbay_Spider import ThotsbayCrawler
from .base_functions import log
from .data_classes import CascadeItem, AsyncRateLimiter


class ScrapeMapper():
    def __init__(self, *, session, include_id=False, thotsbay_auth=None, separate_posts=False):
        self.include_id = include_id
        self.separate_posts = separate_posts
        self.thotsbay_auth = thotsbay_auth
        self.session = session
        self.Cascade = CascadeItem({})

        self.anonfiles_crawler = None
        self.bunkr_crawler = None
        self.cyberdrop_crawler = None
        self.coomer_crawler = None
        self.cyberfile_crawler = None
        self.erome_crawler = None
        self.gfycat_crawler = None
        self.gofile_crawler = None
        self.kemono_crawler = None
        self.pixeldrain_crawler = None
        self.redgifs_crawler = None
        self.saint_crawler = None
        self.sharex_crawler = None
        self.thotsbay_crawler = None

        self.semaphore = asyncio.Semaphore(1)
        self.mapping = {"anonfiles.com": self.Anonfiles, "bunkr.is": self.Bunkr,
                        "bunkr.to": self.Bunkr, "coomer.party": self.coomer,
                        "cyberdrop": self.Cyberdrop, "cyberfile.is": self.cyberfile,
                        "erome.com": self.Erome, "gfycat.com": self.gfycat,
                        "gofile.io": self.GoFile, "jpg.church": self.ShareX,
                        "kemono.party": self.Kemono, "pixeldrain.com": self.Pixeldrain,
                        "pixl.is": self.ShareX, "putme.ga": self.ShareX,
                        "putmega.com": self.ShareX, "redgifs.com": self.redgifs,
                        "saint.to": self.Saint, "thotsbay.com": self.ThotsBay}

    async def Anonfiles(self, url: URL, title=None):
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(include_id=self.include_id)
        domain_obj = await self.anonfiles_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Bunkr(self, url: URL, title=None):
        if not self.bunkr_crawler:
            self.bunkr_crawler = BunkrCrawler(include_id=self.include_id)
        domain_obj = await self.bunkr_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Cyberdrop(self, url: URL, title=None):
        if not self.cyberdrop_crawler:
            self.cyberdrop_crawler = CyberdropCrawler(include_id=self.include_id)
        domain_obj = await self.cyberdrop_crawler.fetch(self.session, url)
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

    async def Kemono(self, url: URL, title=None):
        if not self.kemono_crawler:
            self.kemono_crawler = KemonoCrawler(include_id=self.include_id)
        domain_obj = await self.kemono_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def gfycat(self, url: URL, title=None):
        if not self.gfycat_crawler:
            self.gfycat_crawler = GfycatCrawler(scraping_mapper=self, session=self.session)
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
        if "jpg.church" in url.host:
            async with AsyncRateLimiter(19):
                domain_obj = await self.sharex_crawler.fetch(self.session, url)
        else:
            domain_obj = await self.sharex_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Saint(self, url: URL, title=None):
        if not self.saint_crawler:
            self.saint_crawler = SaintCrawler(include_id=self.include_id)
        domain_obj = await self.saint_crawler.fetch(self.session, url)
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
