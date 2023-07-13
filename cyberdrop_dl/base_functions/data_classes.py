from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, List, Dict, Tuple

if TYPE_CHECKING:
    from yarl import URL


@dataclass
class MediaItem:
    url: URL
    referer: URL
    complete: bool
    filename: str
    ext: str
    original_filename: str

    async def is_complete(self) -> bool:
        return self.complete

    async def mark_completed(self) -> None:
        self.complete = True


@dataclass
class AlbumItem:
    """Class for keeping track of download links for each album"""
    title: str
    media: List[MediaItem]

    async def add_media(self, media_item: MediaItem) -> None:
        self.media.append(media_item)

    async def set_new_title(self, new_title: str) -> None:
        self.title = new_title

    async def append_title(self, title) -> None:
        new_title = title + '/' + self.title
        self.title = new_title

    async def extend(self, album) -> None:
        self.media.extend(album.media)

    async def is_empty(self) -> bool:
        return not self.media


@dataclass
class DomainItem:
    """Class for keeping track of albums for each scraper type"""
    domain: str
    albums: Dict

    async def add_to_album(self, title: str, media: MediaItem) -> None:
        if title in self.albums:
            await self.albums[title].add_media(media)
        else:
            self.albums[title] = AlbumItem(title=title, media=[media])

    async def add_media(self, title: str, media: MediaItem) -> None:
        if title in self.albums:
            album = self.albums[title]
            await album.add_media(media)
        else:
            self.albums[title] = AlbumItem(title, [media])

    async def add_album(self, title: str, album: AlbumItem) -> None:
        if title in self.albums:
            stored_album = self.albums[title]
            for media_item in album.media:
                if media_item in stored_album.media:
                    continue
                await stored_album.add_media(media_item)
        else:
            self.albums[title] = album

    async def set_new_domain(self, domain: str) -> None:
        self.domain = domain

    async def extend(self, domain) -> None:
        for title, album in domain.albums.items():
            await self.add_album(title, album)

    async def append_title(self, title) -> None:
        if not title:
            return
        new_albums = {}
        for album_str, album in self.albums.items():
            new_title = title + '/' + album_str
            new_albums[new_title] = album
            album.title = new_title
        self.albums = new_albums


@dataclass
class CascadeItem:
    """Class for keeping track of domains for each scraper type"""
    domains: Dict

    async def add_albums(self, domain_item: DomainItem) -> None:
        domain = domain_item.domain
        albums = domain_item.albums
        for title, album in albums.items():
            await self.add_album(domain, title, album)

    async def add_to_album(self, domain: str, title: str, media_item: MediaItem) -> None:
        if domain in self.domains:
            await self.domains[domain].add_to_album(title, media_item)
        else:
            self.domains[domain] = DomainItem(domain, {title: AlbumItem(title, [media_item])})

    async def add_album(self, domain: str, title: str, album: AlbumItem) -> None:
        if domain in self.domains:
            await self.domains[domain].add_album(title, album)
        else:
            self.domains[domain] = DomainItem(domain, {title: album})

    async def is_empty(self) -> bool:
        for domain in self.domains.values():
            for album in domain.albums.values():
                if album.media:
                    return False
        return True

    async def get_total(self) -> int:
        total = 0
        for domain in self.domains.values():
            for album in domain.albums.values():
                total += len(album.media)
        return total

    async def append_title(self, title: str) -> None:
        if not title:
            return
        for domain in self.domains.values():
            new_albums = {}
            for album_str, album in domain.albums.items():
                new_title = title + '/' + album_str
                new_albums[new_title] = album
                album.title = new_title
            domain.albums = new_albums

    async def extend(self, Cascade) -> None:
        if Cascade and Cascade.domains:
            for domain_str, domain in Cascade.domains.items():
                for album_str, album in domain.albums.items():
                    await self.add_album(domain_str, album_str, album)

    async def dedupe(self) -> None:
        for domain in self.domains.values():
            for album in domain.albums.values():
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
    threads: Dict

    async def add_album_to_thread(self, title: str, domain: str, album: AlbumItem) -> None:
        if title not in self.threads:
            self.threads[title] = CascadeItem({domain: DomainItem(domain, {album.title: album})})
        else:
            await self.threads[title].add_album(domain, album.title, album)

    async def add_thread(self, title: str, cascade: CascadeItem) -> None:
        if title not in self.threads:
            self.threads[title] = cascade
        else:
            await self.threads[title].extend(cascade)

    async def is_empty(self) -> bool:
        for Cascade in self.threads.values():
            for domain in Cascade.domains.values():
                for album in domain.albums.values():
                    if album.media:
                        return False
        return True

    async def get_total(self) -> int:
        total = 0
        for Cascade in self.threads.values():
            for domain in Cascade.domains.values():
                for album in domain.albums.values():
                    total += len(album.media)
        return total

    async def dedupe(self) -> None:
        for Cascade in self.threads.values():
            for domain in Cascade.domains.values():
                for album in domain.albums.values():
                    check = []
                    allowed = []
                    for media_item in album.media:
                        if media_item.url in check:
                            continue
                        check.append(media_item.url)
                        allowed.append(media_item)
                    album.media = allowed

    async def extend_thread(self, title: str, cascade: CascadeItem) -> None:
        if title in self.threads:
            await self.threads[title].extend(cascade)
        else:
            self.threads[title] = cascade


@dataclass
class FileLock:
    """Rudimentary file lock system"""
    locked_files: List[str] = field(default_factory=list)

    async def check_lock(self, filename: str) -> bool:
        await asyncio.sleep(.1)
        return filename.lower() in self.locked_files

    async def add_lock(self, filename: str) -> None:
        self.locked_files.append(filename.lower())

    async def remove_lock(self, filename: str) -> None:
        self.locked_files.remove(filename.lower())


@dataclass
class SkipData:
    """The allows optoins for domains to skip when scraping"""
    supported_hosts: ClassVar[Tuple[str, ...]] = ("anonfiles", "bayfiles", "bunkr", "coomer.party", "coomer.su",
                                                  "cyberdrop", "cyberfile", "e-hentai", "erome", "fapello", "gfycat",
                                                  "gofile", "hgamecg", "img.kiwi", "imgbox", "jpg.church", "jpg.fish",
                                                  "jpg.fishing", "jpg.pet", "gallery.deltaporno.com", "kemono.party",
                                                  "kemono.su", "lovefap", "nsfw.xxx", "pimpandhost", "pixeldrain",
                                                  "pixl.li", "postimg", "saint", "nudostar", "reddit", "simpcity",
                                                  "socialmediagirls", "xbunker", "xbunkr", "imgur", "redd.it",
                                                  "jpeg.pet", "redgifs")
    sites: List[str]
