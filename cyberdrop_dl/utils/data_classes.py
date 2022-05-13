import asyncio
import collections
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Dict, List, Optional, Tuple, Callable, Awaitable, Any, Type
from random import gauss

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
        if title in self.albums.keys():
            await self.albums[title].add_link_pair(link, referral)
        else:
            self.albums[title] = AlbumItem(
                title=title, link_pairs=[(link, referral)])

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
            self.domains[domain] = DomainItem(
                domain, {title: AlbumItem(title, [(link, referral)])})

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


class AsyncRateLimiter:
    """
    Provides rate limiting for an operation with a configurable number of requests for a time period.
    """

    __lock: asyncio.Lock
    callback: Optional[Callable[[float], Awaitable[Any]]]
    max_calls: int
    period: float
    calls: collections.deque

    def __init__(
        self,
        max_calls: int,
        period: float = 1.0,
        callback: Optional[Callable[[float], Awaitable[Any]]] = None,
    ):
        if period <= 0:
            raise ValueError("Rate limiting period should be > 0")
        if max_calls <= 0:
            raise ValueError("Rate limiting number of calls should be > 0")
        self.calls = collections.deque()

        self.period = period
        self.max_calls = max_calls
        self.callback = callback
        self.__lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncRateLimiter":
        async with self.__lock:
            if len(self.calls) >= self.max_calls:
                until = datetime.utcnow().timestamp() + self.period - self._timespan
                if self.callback:
                    asyncio.ensure_future(self.callback(until))
                sleep_time = until - datetime.utcnow().timestamp()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        async with self.__lock:
            # Store the last operation timestamp.
            self.calls.append(datetime.utcnow().timestamp())

            while self._timespan >= self.period:
                self.calls.popleft()

    @property
    def _timespan(self) -> float:
        return self.calls[-1] - self.calls[0]
