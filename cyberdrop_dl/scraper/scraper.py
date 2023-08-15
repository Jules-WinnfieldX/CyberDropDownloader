from __future__ import annotations

from yarl import URL

from cyberdrop_dl.managers.manager import Manager


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
        self.mapping = {}

    """URL to Function Mapper"""

    async def map_url(self, url_to_map: URL):
        if not url_to_map:
            return
        if not url_to_map.host:
            return

        key = next((key for key in self.mapping if key in url_to_map.host), None)
        if key:
            handler = self.mapping[key]
            await handler(url=url_to_map)
            return
