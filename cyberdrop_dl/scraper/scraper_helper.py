import asyncio
import logging
from typing import Dict

import aiofiles
from myjdapi import myjdapi
from yarl import URL


from ..client.client import Client
from ..client.client import Session
from ..crawlers.Anonfiles_Spider import AnonfilesCrawler
from ..crawlers.Bunkr_Spider import BunkrCrawler
from ..crawlers.Coomer_Spider import CoomerCrawler
from ..crawlers.Cyberdrop_Spider import CyberdropCrawler
from ..crawlers.Cyberfile_Spider import CyberfileCrawler
from ..crawlers.Erome_Spider import EromeCrawler
from ..crawlers.Gfycat_Spider import GfycatCrawler
from ..crawlers.GoFile_Spider import GofileCrawler
from ..crawlers.HGameCG_Spider import HGameCGCrawler
from ..crawlers.ImgBox_Spider import ImgBoxCrawler
from ..crawlers.Kemono_Spider import KemonoCrawler
from ..crawlers.Pixeldrain_Spider import PixelDrainCrawler
from ..crawlers.Postimg_Spider import PostImgCrawler
from ..crawlers.Redgifs_Spider import RedGifsCrawler
from ..crawlers.Rule34_Spider import Rule34Crawler
from ..crawlers.Saint_Spider import SaintCrawler
from ..crawlers.ShareX_Spider import ShareXCrawler
from ..crawlers.SocialMediaGirls_Spider import SocialMediaGirlsCrawler
from ..crawlers.SimpCity_Spider import SimpCityCrawler
from ..crawlers.XBunker_Spider import XBunkerCrawler
from ..crawlers.XBunkr_Spider import XBunkrCrawler
from ..base_functions.base_functions import log, write_last_post_file
from ..base_functions.data_classes import CascadeItem, SkipData, AuthData
from ..client.rate_limiting import AsyncRateLimiter


class ScrapeMapper:
    def __init__(self, *, client: Client, file_args: Dict, jdownloader_args: Dict, runtime_args: Dict,
                 jdownloader_auth: AuthData, simpcity_auth: AuthData, socialmediagirls_auth: AuthData,
                 xbunker_auth: AuthData, skip_data: SkipData, quiet: bool):

        self.include_id = runtime_args['include_id']
        self.quiet = quiet
        self.jdownloader_enable = jdownloader_args['jdownloader_enable']
        self.jdownloader_device = jdownloader_args['jdownloader_device']
        self.separate_posts = runtime_args['separate_posts']
        self.output_last = [runtime_args['output_last_forum_post'], file_args['output_last_forum_post_file']]
        self.xbunker_auth = xbunker_auth
        self.socialmediagirls_auth = socialmediagirls_auth
        self.simpcity_auth = simpcity_auth
        self.jdownloader_auth = jdownloader_auth

        self.client = client
        self.Cascade = CascadeItem({})
        self.skip_data = skip_data

        self.anonfiles_crawler = None
        self.bunkr_crawler = None
        self.cyberdrop_crawler = None
        self.coomer_crawler = None
        self.cyberfile_crawler = None
        self.erome_crawler = None
        self.gfycat_crawler = None
        self.gofile_crawler = None
        self.hgamecg_crawler = None
        self.imgbox_crawler = None
        self.kemono_crawler = None
        self.pixeldrain_crawler = None
        self.postimg_crawler = None
        self.redgifs_crawler = None
        self.rule34_crawler = None
        self.saint_crawler = None
        self.sharex_crawler = None
        self.socialmediagirls_crawler = None
        self.simpcity_crawler = None
        self.xbunker_crawler = None
        self.xbunkr_crawler = None

        self.jdownloader_agent = None

        self.jpgchurch_limiter = AsyncRateLimiter(15)
        self.jpgchurch_semaphore = asyncio.Semaphore(5)
        self.bunkr_limiter = AsyncRateLimiter(15)
        self.forum_limiter = asyncio.Semaphore(4)
        self.semaphore = asyncio.Semaphore(1)

        self.crawlers = [self.anonfiles_crawler, self.bunkr_crawler, self.cyberdrop_crawler, self.coomer_crawler,
                         self.cyberfile_crawler, self.erome_crawler, self.gfycat_crawler, self.gofile_crawler,
                         self.hgamecg_crawler, self.imgbox_crawler, self.kemono_crawler, self.pixeldrain_crawler,
                         self.postimg_crawler, self.redgifs_crawler, self.rule34_crawler, self.saint_crawler,
                         self.sharex_crawler, self.socialmediagirls_crawler, self.simpcity_crawler,
                         self.xbunker_crawler, self.xbunkr_crawler]

        self.mapping = {"anonfiles.com": self.Anonfiles, "bayfiles": self.Anonfiles, "xbunkr": self.XBunkr,
                        "bunkr": self.Bunkr, "coomer.party": self.Coomer, "cyberdrop": self.Cyberdrop,
                        "cyberfile.is": self.Cyberfile, "cyberfile.su": self.Cyberfile, "erome.com": self.Erome,
                        "gfycat.com": self.Gfycat, "gofile.io": self.GoFile, "hgamecg.com": self.HGameCG,
                        "imgbox.com": self.ImgBox, "img.kiwi": self.ShareX, "jpg.church": self.ShareX,
                        "kemono.party": self.Kemono, "pixeldrain.com": self.Pixeldrain, "pixl.li": self.ShareX,
                        "postimg": self.Postimg, "redgifs.com": self.Redgifs, "rule34.xxx": self.Rule34,
                        "saint.to": self.Saint,  "socialmediagirls": self.SocialMediaGirls, "simpcity": self.SimpCity,
                        "xbunker": self.XBunker}

    async def Anonfiles(self, url: URL, title=None):
        anonfiles_session = Session(self.client)
        if not self.anonfiles_crawler:
            self.anonfiles_crawler = AnonfilesCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.anonfiles_crawler.fetch(anonfiles_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await anonfiles_session.exit_handler()

    async def Bunkr(self, url: URL, title=None):
        bunkr_session = Session(self.client)
        if not self.bunkr_crawler:
            self.bunkr_crawler = BunkrCrawler(include_id=self.include_id, quiet=self.quiet)
        async with self.bunkr_limiter:
            domain_obj = await self.bunkr_crawler.fetch(bunkr_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await bunkr_session.exit_handler()

    async def Cyberdrop(self, url: URL, title=None):
        cyberdrop_session = Session(self.client)
        if not self.cyberdrop_crawler:
            self.cyberdrop_crawler = CyberdropCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.cyberdrop_crawler.fetch(cyberdrop_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await cyberdrop_session.exit_handler()

    async def Coomer(self, url: URL, title=None):
        coomer_session = Session(self.client)
        if self.output_last[0]:
            await write_last_post_file(self.output_last[1], str(url))
        if not self.coomer_crawler:
            self.coomer_crawler = CoomerCrawler(include_id=self.include_id, scraping_mapper=self,
                                                separate_posts=self.separate_posts, quiet=self.quiet)
        domain_obj = await self.coomer_crawler.fetch(coomer_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await coomer_session.exit_handler()

    async def Cyberfile(self, url: URL, title=None):
        cyberfile_session = Session(self.client)
        if not self.cyberfile_crawler:
            self.cyberfile_crawler = CyberfileCrawler(quiet=self.quiet)
        async with self.semaphore:
            domain_obj = await self.cyberfile_crawler.fetch(cyberfile_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await cyberfile_session.exit_handler()

    async def Erome(self, url: URL, title=None):
        erome_session = Session(self.client)
        if not self.erome_crawler:
            self.erome_crawler = EromeCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.erome_crawler.fetch(erome_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await erome_session.exit_handler()

    async def GoFile(self, url: URL, title=None):
        gofile_session = Session(self.client)
        if not self.gofile_crawler:
            try:
                self.gofile_crawler = GofileCrawler(quiet=self.quiet)
            except SystemExit:
                await log("Couldn't start the GoFile crawler", quiet=self.quiet)
                return
        domain_obj = await self.gofile_crawler.fetch(gofile_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await gofile_session.exit_handler()

    async def HGameCG(self, url: URL, title=None):
        hgamecg_session = Session(self.client)
        if not self.hgamecg_crawler:
            self.hgamecg_crawler = HGameCGCrawler(quiet=self.quiet)
        domain_obj = await self.hgamecg_crawler.fetch(hgamecg_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await hgamecg_session.exit_handler()

    async def ImgBox(self, url: URL, title=None):
        imgbox_session = Session(self.client)
        if not self.imgbox_crawler:
            self.imgbox_crawler = ImgBoxCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.imgbox_crawler.fetch(imgbox_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await imgbox_session.exit_handler()

    async def Kemono(self, url: URL, title=None):
        kemono_session = Session(self.client)
        if self.output_last[0]:
            await write_last_post_file(self.output_last[1], str(url))
        if not self.kemono_crawler:
            self.kemono_crawler = KemonoCrawler(include_id=self.include_id, scraping_mapper=self,
                                                separate_posts=self.separate_posts, quiet=self.quiet)
        domain_obj = await self.kemono_crawler.fetch(kemono_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await kemono_session.exit_handler()

    async def Gfycat(self, url: URL, title=None):
        gfycat_session = Session(self.client)
        if not self.gfycat_crawler:
            self.gfycat_crawler = GfycatCrawler(quiet=self.quiet)
        content_url = await self.gfycat_crawler.fetch(gfycat_session, url)
        if content_url:
            if title:
                await self.Cascade.add_to_album("gfycat.com", f"{title}/gifs", content_url, url)
            else:
                await self.Cascade.add_to_album("gfycat.com", "gifs", content_url, url)
        await gfycat_session.exit_handler()

    async def Pixeldrain(self, url: URL, title=None):
        pixeldrain_session = Session(self.client)
        if not self.pixeldrain_crawler:
            self.pixeldrain_crawler = PixelDrainCrawler(quiet=self.quiet)
        domain_obj = await self.pixeldrain_crawler.fetch(pixeldrain_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await pixeldrain_session.exit_handler()

    async def Postimg(self, url: URL, title=None):
        postimg_session = Session(self.client)
        if not self.postimg_crawler:
            self.postimg_crawler = PostImgCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.postimg_crawler.fetch(postimg_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await postimg_session.exit_handler()

    async def Redgifs(self, url: URL, title=None):
        redgifs_session = Session(self.client)
        if not self.redgifs_crawler:
            self.redgifs_crawler = RedGifsCrawler(quiet=self.quiet)
        content_url = await self.redgifs_crawler.fetch(redgifs_session, url)
        if content_url:
            if title:
                await self.Cascade.add_to_album("redgifs.com", f"{title}/gifs", content_url, url)
            else:
                await self.Cascade.add_to_album("redgifs.com", "gifs", content_url, url)
        await redgifs_session.exit_handler()

    async def Rule34(self, url: URL, title=None):
        rule34_session = Session(self.client)
        if not self.rule34_crawler:
            self.rule34_crawler = Rule34Crawler(quiet=self.quiet)
        domain_obj = await self.rule34_crawler.fetch(rule34_session, url)
        
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
            
        await rule34_session.exit_handler()

    async def Saint(self, url: URL, title=None):
        saint_session = Session(self.client)
        if not self.saint_crawler:
            self.saint_crawler = SaintCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.saint_crawler.fetch(saint_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await saint_session.exit_handler()

    async def ShareX(self, url: URL, title=None):
        sharex_session = Session(self.client)
        if not self.sharex_crawler:
            self.sharex_crawler = ShareXCrawler(include_id=self.include_id, quiet=self.quiet)
        if "jpg.church" in url.host and sharex_session.client.ratelimit > 19:
            async with self.jpgchurch_semaphore:
                async with self.jpgchurch_limiter:
                    domain_obj = await self.sharex_crawler.fetch(sharex_session, url)
        else:
            domain_obj = await self.sharex_crawler.fetch(sharex_session, url)
        if title:
            await domain_obj.append_title(title)

        await self.Cascade.add_albums(domain_obj)
        await sharex_session.exit_handler()

    async def SocialMediaGirls(self, url: URL, title=None):
        socialmediagirls_session = Session(self.client)
        if not self.socialmediagirls_crawler:
            self.socialmediagirls_crawler = SocialMediaGirlsCrawler(include_id=self.include_id,
                                                                    auth=self.socialmediagirls_auth,
                                                                    scraping_mapper=self,
                                                                    separate_posts=self.separate_posts,
                                                                    output_last=self.output_last, quiet=self.quiet)
        async with self.forum_limiter:
            await self.Cascade.extend(await self.socialmediagirls_crawler.fetch(socialmediagirls_session, url))
        await socialmediagirls_session.exit_handler()

    async def SimpCity(self, url: URL, title=None):
        simpcity_session = Session(self.client)
        if not self.simpcity_crawler:
            self.simpcity_crawler = SimpCityCrawler(include_id=self.include_id, auth=self.simpcity_auth,
                                                    scraping_mapper=self, separate_posts=self.separate_posts,
                                                    output_last=self.output_last, quiet=self.quiet)
        async with self.forum_limiter:
            await self.Cascade.extend(await self.simpcity_crawler.fetch(simpcity_session, url))
        await simpcity_session.exit_handler()

    async def XBunker(self, url: URL, title=None):
        xbunker_session = Session(self.client)
        if not self.xbunker_crawler:
            self.xbunker_crawler = XBunkerCrawler(include_id=self.include_id, auth=self.xbunker_auth,
                                                  scraping_mapper=self, separate_posts=self.separate_posts,
                                                  output_last=self.output_last, quiet=self.quiet)
        async with self.forum_limiter:
            await self.Cascade.extend(await self.xbunker_crawler.fetch(xbunker_session, url))
        await xbunker_session.exit_handler()

    async def XBunkr(self, url: URL, title=None):
        xbunkr_session = Session(self.client)
        if not self.xbunkr_crawler:
            self.xbunkr_crawler = XBunkrCrawler(include_id=self.include_id, quiet=self.quiet)
        domain_obj = await self.xbunkr_crawler.fetch(xbunkr_session, url)
        if title:
            await domain_obj.append_title(title)
        await self.Cascade.add_albums(domain_obj)
        await xbunkr_session.exit_handler()

    async def jdownloader_setup(self):
        try:
            if not self.jdownloader_auth.username or not self.jdownloader_auth.password or not self.jdownloader_device:
                raise Exception("jdownloader credentials were not provided.")
            jd = myjdapi.Myjdapi()
            jd.set_app_key("CYBERDROP-DL")
            jd.connect(self.jdownloader_auth.username, self.jdownloader_auth.password)
            self.jdownloader_agent = jd.get_device(self.jdownloader_device)
        except:
            await log("Failed jdownloader setup", quiet=self.quiet)
            self.jdownloader_enable = False

    async def close(self):
        for crawler in self.crawlers:
            crawler = None


    async def map_url(self, url_to_map: URL, title=None):
        if not url_to_map:
            return
        elif not url_to_map.host:
            await log(str(url_to_map) + " is not supported currently.", quiet=self.quiet)
            return
        for key, value in self.mapping.items():
            if key in url_to_map.host:
                if any(site in key for site in self.skip_data.sites):
                    await log("Skipping scrape of " + str(url_to_map), quiet=self.quiet)
                else:
                    await value(url=url_to_map, title=title)
                return

        if self.jdownloader_enable:
            if not self.jdownloader_agent:
                await self.jdownloader_setup()
            try:
                if "facebook" in url_to_map.host.lower() or "instagram" in url_to_map.host.lower():
                    raise Exception("Blacklisted META")
                await log("Sending " + str(url_to_map) + " to JDownloader", quiet=self.quiet)
                self.jdownloader_agent.linkgrabber.add_links([{
                    "autostart": False,
                    "links": str(url_to_map),
                    "packageName": title if title else "Cyberdrop-DL",
                    "overwritePackagizerRules": True
                    }])
            except Exception as e:
                logging.debug(e)
                await log("Failed to send " + str(url_to_map) + " to JDownloader", quiet=self.quiet)
        else:
            await log("Not Supported: " + str(url_to_map), quiet=self.quiet)
            async with aiofiles.open("./Unsupported_Urls.txt", mode='a') as f:
                await f.write(str(url_to_map)+"\n")
