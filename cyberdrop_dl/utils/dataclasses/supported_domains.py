from dataclasses import dataclass
from typing import ClassVar, Tuple, List


@dataclass
class SupportedDomains:
    """The allows options for domains to skip when scraping"""
    supported_hosts: ClassVar[Tuple[str, ...]] = ("xbunkr", "bunkr", "celebforum", "coomer", "cyberdrop", "cyberfile",
                                                  "e-hentai", "erome", "fapello", "gofile", "ibb.co", "imageban",
                                                  "imgbox", "imgur", "img.kiwi", "jpg.church", "jpg.homes", "jpg.fish",
                                                  "jpg.fishing", "jpg.pet", "jpeg.pet", "jpg1.su", "jpg2.su", "jpg3.su",
                                                  "kemono", "mediafire", "nudostar.com", "nudostar.tv", "pimpandhost",
                                                  "pixeldrain", "postimg", "reddit", "redd.it", "redgifs", "saint",
                                                  "socialmediagirls", "simpcity", "xbunker")
    supported_forums: ClassVar[Tuple[str, ...]] = ("celebforum.to", "nudostar.com", "simpcity.su", "forums.socialmediagirls.com",
                                                   "xbunker.nu")
    supported_forums_map = {"celebforum.to": "celebforum", "nudostar.com": "nudostar", "simpcity.su": "simpcity",
                            "forums.socialmediagirls.com": "socialmediagirls", "xbunker.nu": "xbunker"}

    sites: List[str]
