from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import ClassVar, List, Tuple

from yarl import URL


@dataclass
class MediaItem:
    url: URL
    referer: URL
    complete: bool
    filename: str
    ext: str

    async def is_complete(self):
        return self.complete

    async def mark_completed(self):
        self.complete = True


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: str
    media: List[MediaItem]

    async def add_media(self, media_item: MediaItem):
        self.media.append(media_item)

    async def set_new_title(self, new_title: str):
        self.title = new_title

    async def append_title(self, title):
        new_title = title + '/' + self.title
        self.title = new_title

    async def extend(self, album):
        self.media.extend(album.media)

    async def is_empty(self):
        if not self.media:
            return True
        return False


@dataclass
class DomainItem:
    """Class for keeping track of albums for each scraper type"""
    domain: str
    albums: dict

    async def add_to_album(self, title: str, media: MediaItem):
        if title in self.albums.keys():
            await self.albums[title].add_media(media)
        else:
            self.albums[title] = AlbumItem(title=title, media=[media])

    async def add_media(self, title: str, media: MediaItem):
        if title in self.albums.keys():
            album = self.albums[title]
            await album.add_media(media)
        else:
            self.albums[title] = AlbumItem(title, [media])

    async def add_album(self, title: str, album: AlbumItem):
        if title in self.albums.keys():
            stored_album = self.albums[title]
            for media_item in album.media:
                if media_item in stored_album.media:
                    continue
                await stored_album.add_media(media_item)
        else:
            self.albums[title] = album

    async def set_new_domain(self, domain: str):
        self.domain = domain

    async def extend(self, domain):
        for title, album in domain.albums.items():
            await self.add_album(title, album)

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
    domains: dict

    async def add_albums(self, domain_item: DomainItem):
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            await self.add_album(domain, title, album)

    async def add_to_album(self, domain: str, title: str, media_item: MediaItem):
        if domain in self.domains.keys():
            await self.domains[domain].add_to_album(title, media_item)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [media_item])})

    async def add_album(self, domain: str, title: str, album: AlbumItem):
        if domain in self.domains.keys():
            await self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    async def is_empty(self):
        for _, domain in self.domains.items():
            for _, album in domain.albums.items():
                if album.media:
                    return False
        return True

    async def get_total(self):
        total = 0
        for _, domain in self.domains.items():
            for _, album in domain.albums.items():
                total += len(album.media)
        return total

    async def append_title(self, title: str):
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
                for media_item in album.media:
                    if media_item.url in check:
                        continue
                    check.append(media_item.url)
                    allowed.append(media_item)
                album.media = allowed


@dataclass
class ForumItem:
    """Class for keeping track of forum threads"""
    threads: dict

    async def add_album_to_thread(self, title: str, domain: str, album: AlbumItem):
        if title not in self.threads.keys():
            self.threads[title] = CascadeItem({domain: DomainItem(domain, {album.title: album})})
        else:
            await self.threads[title].add_album(domain, album.title, album)

    async def add_thread(self, title: str, cascade: CascadeItem):
        if title not in self.threads.keys():
            self.threads[title] = cascade
        else:
            await self.threads[title].extend(cascade)

    async def is_empty(self):
        for _, Cascade in self.threads.items():
            for _, domain in Cascade.domains.items():
                for _, album in domain.albums.items():
                    if album.media:
                        return False
        return True

    async def get_total(self):
        total = 0
        for _, Cascade in self.threads.items():
            for _, domain in Cascade.domains.items():
                for _, album in domain.albums.items():
                    total += len(album.media)
        return total

    async def dedupe(self):
        for _, Cascade in self.threads.items():
            for _, domain in Cascade.domains.items():
                for _, album in domain.albums.items():
                    check = []
                    allowed = []
                    for media_item in album.media:
                        if media_item.url in check:
                            continue
                        check.append(media_item.url)
                        allowed.append(media_item)
                    album.media = allowed

    async def extend_thread(self, title: str, cascade: CascadeItem):
        if title in self.threads.keys():
            await self.threads[title].extend(cascade)
        else:
            self.threads[title] = cascade

@dataclass
class FileLock:
    """Rudimentary file lock system"""
    locked_files = []

    async def check_lock(self, filename):
        await asyncio.sleep(.1)
        return filename.lower() in self.locked_files

    async def add_lock(self, filename):
        self.locked_files.append(filename.lower())

    async def remove_lock(self, filename):
        self.locked_files.remove(filename.lower())


@dataclass
class SkipData:
    """The allows optoins for domains to skip when scraping"""
    supported_hosts: ClassVar[Tuple[str]] = ("anonfiles", "bayfiles", "bunkr", "coomer.party", "cyberdrop",
                                             "cyberfile", "e-hentai", "erome", "fapello", "gfycat", "gofile",
                                             "hgamecg", "img.kiwi", "imgbox", "jpg.church", "jpg.fish", "kemono.party",
                                             "lovefap", "nsfw.xxx", "pimpandhost", "pixeldrain", "pixl.li", "postimg",
                                             "saint", "simpcity", "socialmediagirls", "xbunker", "xbunkr")
    sites: List[str]
