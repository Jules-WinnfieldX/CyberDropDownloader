from dataclasses import dataclass
from typing import ClassVar, Tuple, List


@dataclass
class SupportedDomains:
    """The allows options for domains to skip when scraping"""
    supported_hosts: ClassVar[Tuple[str, ...]] = ("anonfiles", "bayfiles", "bunkr", "coomer.party", "coomer.su",
                                                  "cyberdrop", "cyberfile", "e-hentai", "erome", "fapello", "gfycat",
                                                  "gofile", "hgamecg", "img.kiwi", "imgbox", "jpg.church", "jpg.fish",
                                                  "jpg.fishing", "jpg.pet", "jpg1.su", "gallery.deltaporno.com",
                                                  "kemono.su", "lovefap", "nsfw.xxx", "pimpandhost", "pixeldrain",
                                                  "pixl.li", "postimg", "saint", "reddit", "xbunkr", "imgur", "redd.it",
                                                  "jpeg.pet", "redgifs", "kemono.party")
    supported_forums: ClassVar[Tuple[str, ...]] = ("nudostar.com", "simpcity.su", "forums.socialmediagirls.com",
                                                   "xbunker.nu")
    supported_forums_map = {"nudostar.com": "nudostar", "simpcity.su": "simpcity",
                            "forums.socialmediagirls.com": "socialmediagirls", "xbunker.nu": "xbunker"}

    sites: List[str]
