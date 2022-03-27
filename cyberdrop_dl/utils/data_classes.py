from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, AnyStr, Any


@dataclass
class CookiesItem:
    """Class for keeping track of global cookies if needed"""
    cookies: List

    def add_cookies(self, passed_cookies: List):
        if self.cookies is None:
            self.cookies = passed_cookies
        else:
            self.cookies.extend(x for x in passed_cookies if x not in self.cookies)


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: AnyStr
    link_pairs: List[Tuple]
    password: Optional[AnyStr] = None

    def add_link_pair(self, link, referral):
        self.link_pairs.append((link, referral))

    def set_new_title(self, new_title: str):
        self.title = new_title

    def get_title(self):
        return self.title


@dataclass
class DomainItem:
    domain: AnyStr
    albums: Dict[str, Optional[Any]]

    def add_to_album(self, title: str, link: str, referral: str):
        if title in self.albums.keys():
            self.albums[title].add_link_pair(link, referral)
        else:
            self.albums[title] = AlbumItem(title=title, link_pairs=[(link, referral)])

    def add_album(self, title: str, album: AlbumItem):
        i = 1
        original_title = title
        while title in self.albums.keys():
            title = original_title + " - " + str(i)
            album.set_new_title(title)
        self.albums[title] = album


@dataclass
class CascadeItem:
    """Class for keeping track of domains for each scraper type"""
    domains: Dict[str, Optional[Any]]
    cookies = CookiesItem([])

    def add_albums(self, domain_item: DomainItem):
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            self.add_album(domain, title, album)

    def add_to_album(self, domain: str, title: str, link: str, referral: str):
        if domain in self.domains.keys():
            self.domains[domain].add_to_album(title, link, referral)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [(link, referral)])})

    def add_album(self, domain: str, title: str, album: AlbumItem):
        if domain in self.domains.keys():
            self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    def get_albums(self, domain: str):
        if domain in self.domains.keys():
            return self.domains[domain].albums
        else:
            return {}

    def add_cookie(self, cookie: List[Dict]):
        self.cookies.add_cookies(cookie)
