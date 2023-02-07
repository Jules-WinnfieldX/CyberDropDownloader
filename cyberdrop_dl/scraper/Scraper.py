import asyncio
import logging
from typing import Dict, Optional

import aiofiles
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.data_classes import SkipData, CascadeItem, ForumItem, AlbumItem, DomainItem
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.client.client import Client, ScrapeSession
from cyberdrop_dl.client.rate_limiting import AsyncRateLimiter
from cyberdrop_dl.crawlers.Anonfiles_Spider import AnonfilesCrawler
from cyberdrop_dl.crawlers.Bunkr_Spider import BunkrCrawler
from cyberdrop_dl.crawlers.CyberFile_Spider import CyberFileCrawler
from cyberdrop_dl.crawlers.Cyberdrop_Spider import CyberdropCrawler
from cyberdrop_dl.crawlers.Erome_Spider import EromeCrawler
from cyberdrop_dl.crawlers.Fapello_Spider import FapelloCrawler
from cyberdrop_dl.crawlers.Gfycat_Spider import GfycatCrawler
from cyberdrop_dl.crawlers.GoFile_Spider import GoFileCrawler
from cyberdrop_dl.crawlers.HGameCG_Spider import HGameCGCrawler
from cyberdrop_dl.crawlers.ImgBox_Spider import ImgBoxCrawler
from cyberdrop_dl.crawlers.Xenforo_Spider import XenforoCrawler
from cyberdrop_dl.scraper.JDownloader_Integration import JDownloader


class ScrapeMapper:
    def __init__(self, args: Dict, client: Client, SQL_Helper: SQLHelper, quiet: bool):
        self.args = args
        self.client = client
        self.SQL_Helper = SQL_Helper
        self.Cascade = CascadeItem({})
        self.Forums = ForumItem({})
        self.skip_data = SkipData(args['Ignore']['skip_hosts'])

        self.anonfiles_crawler = None
        self.bunkr_crawler = None
        self.cyberdrop_crawler = None
        self.coomer_crawler = None
        self.cyberfile_crawler = None
        self.erome_crawler = None
        self.fapello_crawler = None
        self.gfycat_crawler = None
        self.gofile_crawler = None
        self.hgamecg_crawler = None
        self.imgbox_crawler = None
        self.pixeldrain_crawler = None
        self.postimg_crawler = None
        self.redgifs_crawler = None
        self.rule34_crawler = None
        self.saint_crawler = None
        self.sharex_crawler = None
        self.xbunkr_crawler = None
        self.xenforo_crawler = None

        self.include_id = args['Runtime']['include_id']
        self.quiet = quiet
        self.jdownloader = JDownloader(args['JDownloader'], quiet)

        self.jpgchurch_limiter = AsyncRateLimiter(15)
        self.jpgchurch_semaphore = asyncio.Semaphore(5)
        self.bunkr_limiter = AsyncRateLimiter(15)
        self.forum_limiter = asyncio.Semaphore(4)
        self.semaphore = asyncio.Semaphore(1)

        self.mapping = {"anonfiles": self.Anonfiles, "bunkr": self.Bunkr, "cyberdrop": self.Cyberdrop,
                        "cyberfile": self.CyberFile, "erome": self.Erome, "fapello": self.Fapello,
                        "gfycat": self.Gfycat, "gofile": self.GoFile, "hgamecg": self.HGameCG, "imgbox": self.ImgBox,
                        "simpcity": self.Xenforo, "socialmediagirls": self.Xenforo, "xbunker": self.Xenforo}

    async def handle_additions(self, domain: str, album_obj: Optional[AlbumItem], domain_obj: Optional[DomainItem], title=None):
        if album_obj:
            if title:
                await album_obj.append_title(title)
                await self.Forums.add_album_to_thread(title, domain, album_obj)
            else:
                await self.Cascade.add_album(domain, album_obj.title, album_obj)
        if domain_obj:
            if title:
                await domain_obj.append_title(title)
                for title, album in domain_obj.albums.items():
                    await self.Cascade.add_album(domain, album.title, album)
            else:
                for title, album in domain_obj.albums.items():
                    await self.Cascade.add_album(domain, album.title, album)

    """Regular file host handling"""

    async def Anonfiles(self, url: URL, title=None):
        anonfiles_session = ScrapeSession(self.client)
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.anonfiles_crawler.fetch(anonfiles_session, url)
        await self.handle_additions("anonfiles", album_obj, None, title)
        await anonfiles_session.exit_handler()

    async def Bunkr(self, url: URL, title=None):
        bunkr_session = ScrapeSession(self.client)
        if not self.bunkr_crawler:
            self.bunkr_crawler = BunkrCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        async with self.bunkr_limiter:
            album_obj = await self.bunkr_crawler.fetch(bunkr_session, url)
        if not await album_obj.is_empty():
            await self.handle_additions("bunkr", album_obj, None, title)
        await bunkr_session.exit_handler()

    async def Cyberdrop(self, url: URL, title=None):
        cyberdrop_session = ScrapeSession(self.client)
        if not self.cyberdrop_crawler:
            self.cyberdrop_crawler = CyberdropCrawler(include_id=self.include_id, quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.cyberdrop_crawler.fetch(cyberdrop_session, url)
        await self.handle_additions("cyberdrop", album_obj, None, title)
        await cyberdrop_session.exit_handler()

    async def CyberFile(self, url, title=None):
        cyberfile_session = ScrapeSession(self.client)
        if not self.cyberfile_crawler:
            self.cyberfile_crawler = CyberFileCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        domain_obj = await self.cyberfile_crawler.fetch(cyberfile_session, url)
        await self.handle_additions("cyberfile", None, domain_obj, title)
        await cyberfile_session.exit_handler()

    async def Erome(self, url, title=None):
        erome_session = ScrapeSession(self.client)
        if not self.erome_crawler:
            self.erome_crawler = EromeCrawler(include_id=self.include_id, quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        domain_obj = await self.erome_crawler.fetch(erome_session, url)
        await self.handle_additions("erome", None, domain_obj, title)
        await erome_session.exit_handler()

    async def Gfycat(self, url, title=None):
        gfycat_session = ScrapeSession(self.client)
        if not self.gfycat_crawler:
            self.gfycat_crawler = GfycatCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.gfycat_crawler.fetch(gfycat_session, url)
        await self.handle_additions("gfycat", album_obj, None, title)
        await gfycat_session.exit_handler()

    async def GoFile(self, url, title=None):
        gofile_session = ScrapeSession(self.client)
        if not self.gofile_crawler:
            self.gofile_crawler = GoFileCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        await self.gofile_crawler.get_token(session=gofile_session)
        domain_obj = await self.gofile_crawler.fetch(gofile_session, url)
        await self.handle_additions("gofile", None, domain_obj, title)
        await gofile_session.exit_handler()

    async def HGameCG(self, url, title=None):
        hgamecg_session = ScrapeSession(self.client)
        if not self.hgamecg_crawler:
            self.hgamecg_crawler = HGameCGCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.hgamecg_crawler.fetch(hgamecg_session, url)
        await self.handle_additions("hgamecg", album_obj, None, title)
        await hgamecg_session.exit_handler()

    async def ImgBox(self, url, title=None):
        imgbox_session = ScrapeSession(self.client)
        if not self.hgamecg_crawler:
            self.imgbox_crawler = ImgBoxCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.imgbox_crawler.fetch(imgbox_session, url)
        await self.handle_additions("imgbox", album_obj, None, title)
        await imgbox_session.exit_handler()

    """Archive Sites"""

    async def Fapello(self, url, title=None):
        fapello_session = ScrapeSession(self.client)
        if not self.fapello_crawler:
            self.fapello_crawler = FapelloCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper)
        album_obj = await self.fapello_crawler.fetch(fapello_session, url)
        await self.handle_additions("fapello", album_obj, None, title)
        await fapello_session.exit_handler()

    """Forum handling"""

    async def Xenforo(self, url: URL, title=None):
        xenforo_session = ScrapeSession(self.client)
        if not self.xenforo_crawler:
            self.xenforo_crawler = XenforoCrawler(scraping_mapper=self, args=self.args, SQL_Helper=self.SQL_Helper,
                                                  quiet=self.quiet)
        async with self.forum_limiter:
            cascade, title = await self.xenforo_crawler.fetch(xenforo_session, url)
        if not title or await cascade.is_empty():
            await xenforo_session.exit_handler()
            return
        await self.Forums.add_thread(title, cascade)
        await xenforo_session.exit_handler()

    """URL to Function Mapper"""

    async def map_url(self, url_to_map: URL, title=None):
        if not url_to_map:
            return
        elif not url_to_map.host:
            await log(f"[yellow]Not Supported: {str(url_to_map)}[/yellow]", quiet=self.quiet)
            return
        for key, value in self.mapping.items():
            if key in url_to_map.host:
                if any(site in key for site in self.skip_data.sites):
                    await log(f"[yellow]Skipping: {str(url_to_map)}[/yellow]", quiet=self.quiet)
                else:
                    await value(url=url_to_map, title=title)
                return

        if self.jdownloader.jdownloader_enable:
            async with asyncio.Semaphore(1):
                self.jdownloader.quiet = self.quiet
                if not self.jdownloader.jdownloader_agent:
                    await self.jdownloader.jdownloader_setup()
            await self.jdownloader.direct_unsupported_to_jdownloader(url_to_map, title)

        else:
            await log(f"[yellow]Not Supported: {str(url_to_map)}[/yellow]", quiet=self.quiet)
            async with aiofiles.open(self.args["Files"]["unsupported_urls_file"], mode='a') as f:
                await f.write(str(url_to_map)+"\n")
