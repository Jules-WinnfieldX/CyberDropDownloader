from yarl import URL

from .crawlers.Anonfiles_Spider import AnonfilesCrawler
from .crawlers.Chibisafe_Spider import ChibisafeCrawler
from .crawlers.Erome_Spider import EromeCrawler
from .crawlers.GoFile_Spider import GofileCrawler
from .crawlers.ShareX_Spider import ShareXCrawler
from .crawlers.Thotsbay_Spider import ThotsbayCrawler
from .base_functions import log, pixeldrain_parse
from .data_classes import CascadeItem


class ScrapeMapper():
    def __init__(self, *, session, include_id=False, username=None, password=None):
        self.include_id = include_id
        self.username = username
        self.password = password
        self.session = session
        self.Cascade = CascadeItem({})
        self.erome_crawler = None
        self.sharex_crawler = None
        self.chibisafe_crawler = None
        self.gofile_crawler = None
        self.anonfiles_crawler = None
        self.thotsbay_crawler = None

        self.mapping = {"pixl.is": self.ShareX, "putme.ga": self.ShareX, "putmega.com": self.ShareX,
                        "jpg.church": self.ShareX, "cyberdrop.me": self.Chibisafe, "cyberdrop.cc": self.Chibisafe,
                        "cyberdrop.to": self.Chibisafe, "cyberdrop.nl": self.Chibisafe, "bunkr.is": self.Chibisafe,
                        "bunkr.to": self.Chibisafe, "erome.com": self.Erome, "gofile.io": self.GoFile,
                        "anonfiles.com": self.Anonfiles, "pixeldrain.com": self.Pixeldrain,
                        "thotsbay.com": self.ThotsBay, "socialmediagirls.com": self.ThotsBay}

    async def ShareX(self, url: URL, title=None):
        if not self.sharex_crawler:
            self.sharex_crawler = ShareXCrawler(include_id=self.include_id)
        domain_obj = await self.sharex_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Chibisafe(self, url: URL, title=None):
        if not self.chibisafe_crawler:
            self.chibisafe_crawler = ChibisafeCrawler(include_id=self.include_id)
        domain_obj = await self.chibisafe_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def GoFile(self, url: URL, title=None):
        if not self.gofile_crawler:
            self.gofile_crawler = GofileCrawler()
        domain_obj = await self.gofile_crawler.fetch(self.session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)

    async def Anonfiles(self, url: URL, title=None):
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(include_id=self.include_id)
        domain_obj = await self.anonfiles_crawler.fetch(self.session, url)
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

    async def Pixeldrain(self, url: URL, title=None):
        title_alb = str(url).split('/')[-1]
        title = title + "/" + title_alb if title else title_alb
        await self.Cascade.add_to_album("pixeldrain.com", title, await pixeldrain_parse(url, title), url)

    async def ThotsBay(self, url: URL, title=None):
        if not self.thotsbay_crawler:
            self.thotsbay_crawler = ThotsbayCrawler(include_id=self.include_id, username=self.username, password=self.password, scraping_mapper=self, session=self.session)
        await self.Cascade.extend(await self.thotsbay_crawler.fetch(self.session, url))

    async def map_url(self, url_to_map: URL, title=None):
        for key, value in self.mapping.items():
            if key in url_to_map.host:
                await value(url=url_to_map, title=title)
                return
        await log(str(url_to_map) + "is not supported currently.")
