from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Dict, Optional

from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.data_classes import AlbumItem, CascadeItem, DomainItem, ForumItem, SkipData
from cyberdrop_dl.client.client import Client, ScrapeSession
from cyberdrop_dl.crawlers.Anonfiles_Spider import AnonfilesCrawler
from cyberdrop_dl.crawlers.Bunkr_Spider import BunkrCrawler
from cyberdrop_dl.crawlers.Coomeno_Spider import CoomenoCrawler
from cyberdrop_dl.crawlers.CyberFile_Spider import CyberFileCrawler
from cyberdrop_dl.crawlers.Cyberdrop_Spider import CyberdropCrawler
from cyberdrop_dl.crawlers.EHentai_Spider import EHentaiCrawler
from cyberdrop_dl.crawlers.Erome_Spider import EromeCrawler
from cyberdrop_dl.crawlers.Fapello_Spider import FapelloCrawler
from cyberdrop_dl.crawlers.Gfycat_Spider import GfycatCrawler
from cyberdrop_dl.crawlers.GoFile_Spider import GoFileCrawler
from cyberdrop_dl.crawlers.HGameCG_Spider import HGameCGCrawler
from cyberdrop_dl.crawlers.ImgBox_Spider import ImgBoxCrawler
from cyberdrop_dl.crawlers.Imgur_Spider import ImgurCrawler
from cyberdrop_dl.crawlers.LoveFap_Spider import LoveFapCrawler
from cyberdrop_dl.crawlers.NSFWXXX_Spider import NSFWXXXCrawler
from cyberdrop_dl.crawlers.PimpAndHost_Spider import PimpAndHostCrawler
from cyberdrop_dl.crawlers.PixelDrain_Spider import PixelDrainCrawler
from cyberdrop_dl.crawlers.PostImg_Spider import PostImgCrawler
from cyberdrop_dl.crawlers.RedGifs_Spider import RedGifsCrawler
from cyberdrop_dl.crawlers.Reddit_Spider import RedditCrawler
from cyberdrop_dl.crawlers.Saint_Spider import SaintCrawler
from cyberdrop_dl.crawlers.ShareX_Spider import ShareXCrawler
from cyberdrop_dl.crawlers.XBunkr_Spider import XBunkrCrawler
from cyberdrop_dl.crawlers.Xenforo_Spider import XenforoCrawler
from cyberdrop_dl.scraper.JDownloader_Integration import JDownloader

if TYPE_CHECKING:
    from cyberdrop_dl.base_functions.base_functions import CacheManager, ErrorFileWriter
    from cyberdrop_dl.base_functions.sql_helper import SQLHelper


class ScrapeMapper:
    """This class maps links to their respective handlers, or JDownloader if they are unsupported"""
    def __init__(self, args: Dict, client: Client, SQL_Helper: SQLHelper, quiet: bool, error_writer: ErrorFileWriter,
                 cache_manager: CacheManager):
        self.args = args
        self.client = client
        self.SQL_Helper = SQL_Helper
        self.Cascade = CascadeItem({})
        self.Forums = ForumItem({})
        self.skip_coomer_ads = args['Ignore']['skip_coomer_ads']
        self.skip_data = SkipData(args['Ignore']['skip_hosts'])
        self.only_data = SkipData(args['Ignore']['only_hosts'])

        self.cache_manager = cache_manager
        self.error_writer = error_writer

        self.anonfiles_crawler: Optional[AnonfilesCrawler] = None
        self.bunkr_crawler: Optional[BunkrCrawler] = None
        self.cyberdrop_crawler: Optional[CyberdropCrawler] = None
        self.coomeno_crawler: Optional[CoomenoCrawler] = None
        self.cyberfile_crawler: Optional[CyberFileCrawler] = None
        self.ehentai_crawler: Optional[EHentaiCrawler] = None
        self.erome_crawler: Optional[EromeCrawler] = None
        self.fapello_crawler: Optional[FapelloCrawler] = None
        self.gfycat_crawler: Optional[GfycatCrawler] = None
        self.gofile_crawler: Optional[GoFileCrawler] = None
        self.hgamecg_crawler: Optional[HGameCGCrawler] = None
        self.imgur_crawler: Optional[ImgurCrawler] = None
        self.imgbox_crawler: Optional[ImgBoxCrawler] = None
        self.lovefap_crawler: Optional[LoveFapCrawler] = None
        self.nsfwxxx_crawler: Optional[NSFWXXXCrawler] = None
        self.pimpandhost_crawler: Optional[PimpAndHostCrawler] = None
        self.pixeldrain_crawler: Optional[PixelDrainCrawler] = None
        self.postimg_crawler: Optional[PostImgCrawler] = None
        self.reddit_crawler: Optional[RedditCrawler] = None
        self.redgifs_crawler: Optional[RedGifsCrawler] = None
        self.saint_crawler: Optional[SaintCrawler] = None
        self.sharex_crawler: Optional[ShareXCrawler] = None
        self.xbunkr_crawler: Optional[XBunkrCrawler] = None
        self.xenforo_crawler: Optional[XenforoCrawler] = None

        self.include_id = args['Runtime']['include_id']
        self.remove_bunkr_id = args['Runtime']['remove_bunkr_identifier']
        self.separate_posts = args["Forum_Options"]["separate_posts"]
        self.quiet = quiet
        self.jdownloader = JDownloader(args['JDownloader'], quiet)

        self.coomero_semaphore = asyncio.Semaphore(4)
        self.gofile_semaphore = asyncio.Semaphore(1)
        self.nudostar_semaphore = asyncio.Semaphore(1)
        self.simpcity_semaphore = asyncio.Semaphore(1)
        self.socialmediagirls_semaphore = asyncio.Semaphore(1)
        self.xbunker_semaphore = asyncio.Semaphore(1)

        self.mapping = {"anonfiles": self.Anonfiles, "bayfiles": self.Anonfiles, "xbunkr": self.XBunkr,
                        "bunkr": self.Bunkr, "cyberdrop": self.Cyberdrop, "cyberfile": self.CyberFile,
                        "erome": self.Erome, "fapello": self.Fapello, "gfycat": self.Gfycat, "gofile": self.GoFile,
                        "hgamecg": self.HGameCG, "imgbox": self.ImgBox, "pixeldrain": self.PixelDrain,
                        "postimg": self.PostImg, "saint": self.Saint, "img.kiwi": self.ShareX, "imgur": self.Imgur,
                        "jpg.church": self.ShareX, "jpg.fish": self.ShareX, "jpg.pet": self.ShareX,
                        "jpeg.pet": self.ShareX, "pixl.li": self.ShareX, "nsfw.xxx": self.NSFW_XXX,
                        "pimpandhost": self.PimpAndHost, "lovefap": self.LoveFap, "e-hentai": self.EHentai,
                        "gallery.deltaporno": self.ShareX, "vk.com": self.vk_redirect, "coomer.party": self.Coomeno,
                        "coomer.su": self.Coomeno, "kemono.party": self.Coomeno, "kemono.su": self.Coomeno,
                        "nudostar": self.Xenforo, "simpcity": self.Xenforo, "socialmediagirls": self.Xenforo,
                        "xbunker": self.Xenforo, "reddit": self.Reddit, "redd.it": self.Reddit, "redgifs": self.RedGifs}

    async def _handle_album_additions(self, domain: str, album_obj: AlbumItem, title=None) -> None:
        if title:
            await album_obj.append_title(title)
            await self.Forums.add_album_to_thread(title, domain, album_obj)
        else:
            await self.Cascade.add_album(domain, album_obj.title, album_obj)

    async def _handle_domain_additions(self, domain: str, domain_obj: DomainItem, title=None) -> None:
        if title:
            await domain_obj.append_title(title)
            for album in domain_obj.albums.values():
                await self.Forums.add_album_to_thread(title, domain, album)
        else:
            for album in domain_obj.albums.values():
                await self.Cascade.add_album(domain, album.title, album)

    """Redirection handler for Simp City"""

    async def vk_redirect(self, url: URL, title=None):
        url = URL(url.query['to'])
        await self.map_url(url, title)

    """Regular file host handling"""

    async def Anonfiles(self, url: URL, title=None):
        anonfiles_session = ScrapeSession(self.client)
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                      error_writer=self.error_writer)
        album_obj = await self.anonfiles_crawler.fetch(anonfiles_session, url)
        await self._handle_album_additions("anonfiles", album_obj, title)
        await anonfiles_session.exit_handler()

    async def Bunkr(self, url: URL, title=None):
        bunkr_session = ScrapeSession(self.client)
        if not self.bunkr_crawler:
            self.bunkr_crawler = BunkrCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                              remove_bunkr_id=self.remove_bunkr_id, error_writer=self.error_writer)

        album_obj = await self.bunkr_crawler.fetch(bunkr_session, url)
        if not await album_obj.is_empty():
            await self._handle_album_additions("bunkr", album_obj, title)
        await bunkr_session.exit_handler()

    async def Cyberdrop(self, url: URL, title=None):
        cyberdrop_session = ScrapeSession(self.client)
        if not self.cyberdrop_crawler:
            self.cyberdrop_crawler = CyberdropCrawler(include_id=self.include_id, quiet=self.quiet,
                                                      SQL_Helper=self.SQL_Helper, error_writer=self.error_writer)
        album_obj = await self.cyberdrop_crawler.fetch(cyberdrop_session, url)
        await self._handle_album_additions("cyberdrop", album_obj, title)
        await cyberdrop_session.exit_handler()

    async def CyberFile(self, url, title=None):
        cyberfile_session = ScrapeSession(self.client)
        if not self.cyberfile_crawler:
            self.cyberfile_crawler = CyberFileCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                      error_writer=self.error_writer)

        domain_obj = await self.cyberfile_crawler.fetch(cyberfile_session, url)
        await self._handle_domain_additions("cyberfile", domain_obj, title)
        await cyberfile_session.exit_handler()

    async def EHentai(self, url, title=None):
        ehentai_session = ScrapeSession(self.client)
        if not self.ehentai_crawler:
            self.ehentai_crawler = EHentaiCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                  error_writer=self.error_writer)
        album_obj = await self.ehentai_crawler.fetch(ehentai_session, url)
        await self._handle_album_additions("e-hentai", album_obj, title)
        await ehentai_session.exit_handler()

    async def Erome(self, url, title=None):
        erome_session = ScrapeSession(self.client)
        if not self.erome_crawler:
            self.erome_crawler = EromeCrawler(include_id=self.include_id, quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                              error_writer=self.error_writer)
        domain_obj = await self.erome_crawler.fetch(erome_session, url)
        await self._handle_domain_additions("erome", domain_obj, title)
        await erome_session.exit_handler()

    async def Gfycat(self, url, title=None):
        gfycat_session = ScrapeSession(self.client)
        if not self.gfycat_crawler:
            self.gfycat_crawler = GfycatCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                error_writer=self.error_writer)
        album_obj = await self.gfycat_crawler.fetch(gfycat_session, url)
        await self._handle_album_additions("gfycat", album_obj, title)
        await gfycat_session.exit_handler()

    async def GoFile(self, url, title=None):
        gofile_session = ScrapeSession(self.client)
        if not self.gofile_crawler:
            self.gofile_crawler = GoFileCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                error_writer=self.error_writer, cache_manager=self.cache_manager)

        async with self.gofile_semaphore:
            await self.gofile_crawler.get_acct_token(session=gofile_session,
                                                     api_token=self.args['Authentication']['gofile_api_key'])
            await self.gofile_crawler.get_website_token(session=gofile_session,
                                                        website_token=self.args['Authentication']['gofile_website_token'])
        domain_obj = await self.gofile_crawler.fetch(gofile_session, url)
        await self._handle_domain_additions("gofile", domain_obj, title)
        await gofile_session.exit_handler()

    async def HGameCG(self, url, title=None):
        hgamecg_session = ScrapeSession(self.client)
        if not self.hgamecg_crawler:
            self.hgamecg_crawler = HGameCGCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                  error_writer=self.error_writer)
        album_obj = await self.hgamecg_crawler.fetch(hgamecg_session, url)
        await self._handle_album_additions("hgamecg", album_obj, title)
        await hgamecg_session.exit_handler()

    async def ImgBox(self, url, title=None):
        imgbox_session = ScrapeSession(self.client)
        if not self.imgbox_crawler:
            self.imgbox_crawler = ImgBoxCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                error_writer=self.error_writer)
        album_obj = await self.imgbox_crawler.fetch(imgbox_session, url)
        await self._handle_album_additions("imgbox", album_obj, title)
        await imgbox_session.exit_handler()

    async def Imgur(self, url, title=None):
        imgur_session = ScrapeSession(self.client)
        if not self.imgur_crawler:
            self.imgur_crawler = ImgurCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                              separate_posts=self.separate_posts, error_writer=self.error_writer,
                                              args=self.args)
        domain_obj = await self.imgur_crawler.fetch(imgur_session, url)
        await self._handle_domain_additions("imgur", domain_obj, title)
        await imgur_session.exit_handler()

    async def LoveFap(self, url: URL, title=None):
        lovefap_session = ScrapeSession(self.client)
        if not self.lovefap_crawler:
            self.lovefap_crawler = LoveFapCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                  error_writer=self.error_writer)
        album_obj = await self.lovefap_crawler.fetch(lovefap_session, url)
        await self._handle_album_additions("lovefap", album_obj, title)
        await lovefap_session.exit_handler()

    async def PimpAndHost(self, url, title=None):
        pimpandhost_session = ScrapeSession(self.client)
        if not self.pimpandhost_crawler:
            self.pimpandhost_crawler = PimpAndHostCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                          error_writer=self.error_writer)
        album_obj = await self.pimpandhost_crawler.fetch(pimpandhost_session, url)
        await self._handle_album_additions("pimpandhost", album_obj, title)
        await pimpandhost_session.exit_handler()

    async def PixelDrain(self, url, title=None):
        pixeldrain_session = ScrapeSession(self.client)
        if not self.pixeldrain_crawler:
            self.pixeldrain_crawler = PixelDrainCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                        error_writer=self.error_writer)
        album_obj = await self.pixeldrain_crawler.fetch(pixeldrain_session, url)
        await self._handle_album_additions("pixeldrain", album_obj, title)
        await pixeldrain_session.exit_handler()

    async def PostImg(self, url, title=None):
        postimg_session = ScrapeSession(self.client)
        if not self.postimg_crawler:
            self.postimg_crawler = PostImgCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                  error_writer=self.error_writer)
        album_obj = await self.postimg_crawler.fetch(postimg_session, url)
        await self._handle_album_additions("postimg", album_obj, title)
        await postimg_session.exit_handler()

    async def Reddit(self, url, title=None):
        reddit_session = ScrapeSession(self.client)
        if not self.reddit_crawler:
            self.reddit_crawler = RedditCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                separate_posts=self.separate_posts, error_writer=self.error_writer,
                                                args=self.args, scraping_mapper=self)
        domain_obj = await self.reddit_crawler.fetch(url)
        await self._handle_domain_additions("reddit", domain_obj, title)
        await reddit_session.exit_handler()

    async def RedGifs(self, url, title=None):
        redgifs_session = ScrapeSession(self.client)
        if not self.redgifs_crawler:
            self.redgifs_crawler = RedGifsCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                              separate_posts=self.separate_posts, error_writer=self.error_writer)
        domain_obj = await self.redgifs_crawler.fetch(redgifs_session, url)
        await self._handle_domain_additions("redgifs", domain_obj, title)
        await redgifs_session.exit_handler()

    async def Saint(self, url, title=None):
        saint_session = ScrapeSession(self.client)
        if not self.saint_crawler:
            self.saint_crawler = SaintCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                              error_writer=self.error_writer)
        album_obj = await self.saint_crawler.fetch(saint_session, url)
        await self._handle_album_additions("saint", album_obj, title)
        await saint_session.exit_handler()

    async def ShareX(self, url, title=None):
        sharex_session = ScrapeSession(self.client)
        if not self.sharex_crawler:
            self.sharex_crawler = ShareXCrawler(include_id=self.include_id, quiet=self.quiet,
                                                SQL_Helper=self.SQL_Helper, error_writer=self.error_writer)

        domain_obj = await self.sharex_crawler.fetch(sharex_session, url)
        await self._handle_domain_additions("sharex", domain_obj, title)
        await sharex_session.exit_handler()

    async def XBunkr(self, url, title=None):
        xbunkr_session = ScrapeSession(self.client)
        if not self.xbunkr_crawler:
            self.xbunkr_crawler = XBunkrCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                error_writer=self.error_writer)
        album_obj = await self.xbunkr_crawler.fetch(xbunkr_session, url)
        await self._handle_album_additions("xbunkr", album_obj, title)
        await xbunkr_session.exit_handler()

    """Archive Sites"""

    async def Fapello(self, url, title=None):
        fapello_session = ScrapeSession(self.client)
        if not self.fapello_crawler:
            self.fapello_crawler = FapelloCrawler(quiet=self.quiet, SQL_Helper=self.SQL_Helper,
                                                  error_writer=self.error_writer)
        album_obj = await self.fapello_crawler.fetch(fapello_session, url)
        if album_obj:
            await self._handle_album_additions("fapello", album_obj, title)
        await fapello_session.exit_handler()

    async def NSFW_XXX(self, url, title=None):
        nsfwxxx_session = ScrapeSession(self.client)
        if not self.nsfwxxx_crawler:
            self.nsfwxxx_crawler = NSFWXXXCrawler(separate_posts=self.separate_posts, quiet=self.quiet,
                                                  SQL_Helper=self.SQL_Helper, error_writer=self.error_writer)
        domain_obj = await self.nsfwxxx_crawler.fetch(nsfwxxx_session, url)
        await self._handle_domain_additions("nsfw.xxx", domain_obj, title)
        await nsfwxxx_session.exit_handler()

    async def Coomeno(self, url: URL, title=None):
        coomeno_session = ScrapeSession(self.client)
        if not self.coomeno_crawler:
            self.coomeno_crawler = CoomenoCrawler(include_id=self.include_id, scraping_mapper=self,
                                                  separate_posts=self.separate_posts,
                                                  skip_coomer_ads=self.skip_coomer_ads, SQL_Helper=self.SQL_Helper,
                                                  quiet=self.quiet, error_writer=self.error_writer)
        assert url.host is not None
        async with self.coomero_semaphore:
            cascade, new_title = await self.coomeno_crawler.fetch(coomeno_session, url)

        if not new_title or await cascade.is_empty():
            await coomeno_session.exit_handler()
            return
        if title:
            await cascade.append_title(title)
            await self.Forums.extend_thread(title, cascade)
        else:
            await self.Forums.add_thread(new_title, cascade)
        await coomeno_session.exit_handler()

    """Forum handling"""

    async def Xenforo(self, url: URL, title=None):
        xenforo_session = ScrapeSession(self.client)
        if not self.xenforo_crawler:
            self.xenforo_crawler = XenforoCrawler(scraping_mapper=self, args=self.args, SQL_Helper=self.SQL_Helper,
                                                  quiet=self.quiet, error_writer=self.error_writer)
        title = None
        cascade = None

        assert self.xenforo_crawler is not None and url.host is not None
        if "simpcity" in url.host:
            async with self.simpcity_semaphore:
                cascade, title = await self.xenforo_crawler.fetch(xenforo_session, url)
        elif "socialmediagirls" in url.host:
            async with self.socialmediagirls_semaphore:
                cascade, title = await self.xenforo_crawler.fetch(xenforo_session, url)
        elif "xbunker" in url.host:
            async with self.xbunker_semaphore:
                cascade, title = await self.xenforo_crawler.fetch(xenforo_session, url)
        elif "nudostar" in url.host:
            async with self.nudostar_semaphore:
                cascade, title = await self.xenforo_crawler.fetch(xenforo_session, url)

        assert cascade is not None
        if not title or await cascade.is_empty():
            await xenforo_session.exit_handler()
            return

        await self.Forums.add_thread(title, cascade)
        await xenforo_session.exit_handler()

    """URL to Function Mapper"""

    async def is_skip_host(self, host: str) -> bool:
        if self.only_data.sites:
            return not any(site in host for site in self.only_data.sites)
        return any(site in host for site in self.skip_data.sites)

    async def map_url(self, url_to_map: URL, title=None, referer: Optional[URL] = None):
        if not url_to_map:
            return
        if not url_to_map.host:
            log(f"Not Supported: {url_to_map}", quiet=self.quiet, style="yellow")
            return

        key = next((key for key in self.mapping if key in url_to_map.host), None)
        if key:
            if await self.is_skip_host(key):
                log(f"Skipping: {url_to_map}", quiet=self.quiet, style="yellow")
            else:
                handler = self.mapping[key]
                await handler(url=url_to_map, title=title)
            return

        if self.jdownloader.jdownloader_enable:
            await self.jdownloader.direct_unsupported_to_jdownloader(url_to_map, title)

        else:
            log(f"Not Supported: {url_to_map}", quiet=self.quiet, style="yellow")
            if not referer:
                referer = URL("")
            if not title:
                title = ""
            title = title.encode("ascii", "ignore")
            title = title.decode().strip()
            await self.error_writer.write_unsupported(url_to_map, referer, title)
