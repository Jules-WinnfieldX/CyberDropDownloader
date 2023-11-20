from dataclasses import dataclass
from typing import ClassVar, Tuple, List


@dataclass
class SupportedDomains:
    """The allows options for domains to skip when scraping"""
    supported_hosts: ClassVar[Tuple[str, ...]] = ("bunkr", "coomer", "coomer", "cyberdrop", "cyberfile", "e-hentai",
                                                  "erome", "fapello", "gofile", "imgbox", "imgur", "img.kiwi", "jpg.church",
                                                  "jpg.fish", "jpg.homes", "jpg.fishing", "jpg.pet", "jpeg.pet",
                                                  "jpg1.su", "jpg2.su", "jpg3.su", "kemono", "pimpandhost",
                                                  "pixeldrain", "postimg", "saint", "reddit", "redd.it", "redgifs",
                                                  "xbunkr")
    supported_forums: ClassVar[Tuple[str, ...]] = ("nudostar.com", "simpcity.su", "forums.socialmediagirls.com",
                                                   "xbunker.nu")
    supported_forums_map = {"nudostar.com": "nudostar", "simpcity.su": "simpcity",
                            "forums.socialmediagirls.com": "socialmediagirls", "xbunker.nu": "xbunker"}

    sites: List[str]
