import asyncio
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Tuple

from yarl import URL


@dataclass
class FileLock:
    locked_files = []

    async def check_lock(self, filename):
        await asyncio.sleep(.1)
        return filename.lower() in self.locked_files

    async def add_lock(self, filename):
        self.locked_files.append(filename.lower())

    async def remove_lock(self, filename):
        self.locked_files.remove(filename.lower())


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: str
    link_pairs: List[Tuple]
    password: Optional[str] = None

    async def add_link_pair(self, link, referral):
        self.link_pairs.append((link, referral))

    async def set_new_title(self, new_title: str):
        self.title = new_title

    async def get_referrer(self, link: URL):
        for pair in self.link_pairs:
            if link == pair[0]:
                return pair[1]

    async def replace_link_pairs(self, link_pairs_in):
        map = {}
        for link_pair in link_pairs_in:
            for pair in self.link_pairs:
                if link_pair[0].parts[-1] == pair[0].parts[-1]:
                    self.link_pairs.remove(pair)
                    self.link_pairs.append(link_pair)
                    map[pair[0]] = link_pair[0]
        return map


@dataclass
class DomainItem:
    domain: str
    albums: Dict[str, AlbumItem]

    async def add_to_album(self, title: str, link: URL, referral: URL):
        if link:
            if title in self.albums.keys():
                await self.albums[title].add_link_pair(link, referral)
            else:
                self.albums[title] = AlbumItem(title=title, link_pairs=[(link, referral)])

    async def add_album(self, title: str, album: AlbumItem):
        if title in self.albums.keys():
            stored_album = self.albums[title]
            for link_pair in album.link_pairs:
                link, referral = link_pair
                await stored_album.add_link_pair(link, referral)
        else:
            self.albums[title] = album

    async def append_title(self, title):
        if not title:
            return
        new_albums = {}
        for album_str, album in self.albums.items():
            new_title = title+'/'+album_str
            new_albums[new_title] = album
            album.title = new_title
        self.albums = new_albums


@dataclass
class CascadeItem:
    """Class for keeping track of domains for each scraper type"""
    domains: Dict[str, DomainItem]

    async def add_albums(self, domain_item: DomainItem):
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            await self.add_album(domain, title, album)

    async def add_to_album(self, domain: str, title: str, link: URL, referral: URL):
        if domain in self.domains.keys():
            await self.domains[domain].add_to_album(title, link, referral)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [(link, referral)])})

    async def add_album(self, domain: str, title: str, album: AlbumItem):
        if domain in self.domains.keys():
            await self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    async def is_empty(self):
        for _, domain in self.domains.items():
            for _, album in domain.albums.items():
                if album.link_pairs:
                    return False
        return True

    async def append_title(self, title):
        if not title:
            return
        for _, domain in self.domains.items():
            new_albums = {}
            for album_str, album in domain.albums.items():
                new_title = title+'/'+album_str
                new_albums[new_title] = album
                album.title = new_title
            domain.albums = new_albums

    async def extend(self, Cascade):
        if Cascade:
            if Cascade.domains:
                for domain_str, domain in Cascade.domains.items():
                    for album_str, album in domain.albums.items():
                        await self.add_album(domain_str, album_str, album)

    async def dedupe(self):
        for _, domain in self.domains.items():
            for _, album in domain.albums.items():
                check = []
                allowed = []
                for pair in album.link_pairs:
                    url, _ = pair
                    if url in check:
                        continue
                    check.append(url)
                    allowed.append(pair)
                album.link_pairs = allowed


@dataclass
class AuthData:
    """Class for keeping username and password"""
    username: str
    password: str


@dataclass
class SkipData:
    supported_hosts: ClassVar[Tuple[str]] = (
        "anonfiles", "bayfiles", "bunkr", "coomer.party", "cyberdrop", "cyberfile", "erome", "gfycat", "gofile",
        "hgamecg", "imgbox", "img.kiwi", "jpg.church", "kemono.party", "pixeldrain", "pixl.li", "postimg.cc",
        "redgifs", "rule34", "saint", "socialmediagirls", "simpcity", "xbunker", "xbunkr")
    sites: List[str]
