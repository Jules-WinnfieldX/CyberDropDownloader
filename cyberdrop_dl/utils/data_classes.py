from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, AnyStr, Any

import aiohttp
from yarl import *


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: str
    link_pairs: List[Tuple]
    password: Optional[str] = None

    def add_link_pair(self, link, referral):
        self.link_pairs.append((link, referral))

    def set_new_title(self, new_title: str):
        self.title = new_title


@dataclass
class DomainItem:
    domain: str
    albums: Dict[str, AlbumItem]

    def add_to_album(self, title: str, link: URL, referral: URL):
        if title in self.albums.keys():
            self.albums[title].add_link_pair(link, referral)
        else:
            self.albums[title] = AlbumItem(title=title, link_pairs=[(link, referral)])

    def add_album(self, title: str, album: AlbumItem):
        if title in self.albums.keys():
            stored_album = self.albums[title]
            for link_pair in album.link_pairs:
                link, referral = link_pair
                stored_album.add_link_pair(link, referral)
        else:
            self.albums[title] = album


@dataclass
class CascadeItem:
    """Class for keeping track of domains for each scraper type"""
    domains: Dict[str, DomainItem]
    cookies: aiohttp.CookieJar = None

    def add_albums(self, domain_item: DomainItem):
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            self.add_album(domain, title, album)

    def add_to_album(self, domain: str, title: str, link: URL, referral: URL):
        if domain in self.domains.keys():
            self.domains[domain].add_to_album(title, link, referral)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [(link, referral)])})

    def add_album(self, domain: str, title: str, album: AlbumItem):
        if domain in self.domains.keys():
            self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    def is_empty(self):
        for domain_str, domain in self.domains.items():
            for album_str, album in domain.albums.items():
                if album.link_pairs:
                    return False
        return True

    def append_title(self, title):
        for domain_str, domain in self.domains.items():
            new_albums = {}
            for album_str, album in domain.albums.items():
                new_title = title+'/'+album_str
                new_albums[new_title] = album
                album.title = new_title
            domain.albums = new_albums

    def extend(self, Cascade):
        for domain_str, domain in Cascade.domains.items():
            for album_str, album in domain.albums.items():
                self.add_album(domain_str, album_str, album)
