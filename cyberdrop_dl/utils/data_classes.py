import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import aiohttp
from yarl import URL


@dataclass
class FileLock:
    locked_files = []

    async def check_lock(self, filename):
        await asyncio.sleep(.1)
        if filename.lower() in self.locked_files:
            return True
        return False

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
    cookies: aiohttp.CookieJar = None

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
        for domain_str, domain in self.domains.items():
            for album_str, album in domain.albums.items():
                if album.link_pairs:
                    return False
        return True

    async def append_title(self, title):
        if not title:
            return
        for domain_str, domain in self.domains.items():
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
        for domain_str, domain in self.domains.items():
            for album_str, album in domain.albums.items():
                check = []
                allowed = []
                for pair in album.link_pairs:
                    url, referrer = pair
                    if url in check:
                        continue
                    else:
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
    sites = {"anonfiles.com": False, "bunkr": False, "coomer.party": False,
             "cyberdrop": False, "cyberfile.is": False, "erome.com": False, "gfycat.com": False,
             "gofile.io": False, "jpg.church": False, "kemono.party": False, "pixeldrain.com": False,
             "pixl.is": False, "putme.ga": False, "putmega.com": False, "redgifs.com": False,
             "saint.to": False, "thotsbay.com": False}

    async def add_skips(self, anonfiles, bunkr, coomer, cyberdrop, cyberfile, erome, gfycat, gofile, jpgchurch,
                        kemono, pixeldrain, pixl, putmega, redgifs, saint):
        if anonfiles:
            self.sites['anonfiles.com'] = True
        if bunkr:
            self.sites['bunkr'] = True
        if coomer:
            self.sites['coomer.party'] = True
        if cyberdrop:
            self.sites['cyberdrop'] = True
        if cyberfile:
            self.sites['cyberfile.is'] = True
        if erome:
            self.sites['erome.com'] = True
        if gfycat:
            self.sites['gfycat.com'] = True
        if gofile:
            self.sites['gofile.io'] = True
        if jpgchurch:
            self.sites['jpg.church'] = True
        if kemono:
            self.sites['kemono.party'] = True
        if pixeldrain:
            self.sites['pixeldrain.com'] = True
        if pixl:
            self.sites['pixl.is'] = True
        if putmega:
            self.sites['putme.ga'] = True
            self.sites['putmega.com'] = True
        if redgifs:
            self.sites['redgifs.com'] = True
        if saint:
            self.sites['saint.to'] = True

