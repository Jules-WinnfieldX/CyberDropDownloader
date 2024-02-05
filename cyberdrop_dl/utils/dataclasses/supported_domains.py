from dataclasses import dataclass
from typing import ClassVar, Tuple, List


@dataclass
class SupportedDomains:
    """The allows options for domains to skip when scraping and mappings"""
    supported_hosts: ClassVar[Tuple[str, ...]] = ("bunkr", "bunkrr", "celebforum", "coomer", "cyberdrop", "cyberfile",
                                                  "e-hentai", "erome", "fapello", "f95zone", "gofile", "hotpic",
                                                  "ibb.co", "imageban", "imgbox", "imgur", "img.kiwi", "jpg.church",
                                                  "jpg.homes", "jpg.fish", "jpg.fishing", "jpg.pet", "jpeg.pet",
                                                  "jpg1.su", "jpg2.su", "jpg3.su", "jpg4.su", "host.church", "kemono",
                                                  "leakedmodels", "mediafire", "nudostar.com", "nudostar.tv",
                                                  "omegascans", "pimpandhost", "pixeldrain", "postimg", "reddit",
                                                  "redd.it", "redgifs", "rule34.xxx", "rule34.xyz", "saint",
                                                  "scrolller", "simpcity", "socialmediagirls", "toonily", "xbunker",
                                                  "xbunkr")

    supported_forums: ClassVar[Tuple[str, ...]] = ("celebforum.to", "f95zone.to", "leakedmodels.com", "nudostar.com",
                                                   "simpcity.su", "forums.socialmediagirls.com", "xbunker.nu")
    supported_forums_map = {"celebforum.to": "celebforum", "f95zone.to": "f95zone", "leakedmodels.com": "leakedmodels",
                            "nudostar.com": "nudostar", "simpcity.su": "simpcity",
                            "forums.socialmediagirls.com": "socialmediagirls", "xbunker.nu": "xbunker"}

    supported_ddos_guard: ClassVar[Tuple[str, ...]] = (".bunkrr.su", ".coomer.su", ".kemono.su")
    supported_ddos_guard_map = {".bunkrr.su": "bunkrr", ".coomer.su": "coomer", ".kemono.su": "kemono"}

    sites: List[str]
