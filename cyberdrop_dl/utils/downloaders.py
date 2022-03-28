import asyncio
from functools import wraps
import http
import multiprocessing
from pathlib import Path
import ssl
import time
import traceback

import aiofiles
import aiofiles.os
import aiohttp
import aiohttp.client_exceptions
import certifi
from tqdm import tqdm
import yarl

from .base_functions import *
from .data_classes import *


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""
    pass


def retry(f):
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        for i in range(self.attempts):
            try:
                return await f(self, *args, **kwargs)
            except FailureException:
                if i == self.attempts - 1:
                    raise
                logger.debug('Retrying...')
                time.sleep(4)
    return wrapper


async def throttle(self, url: yarl.URL) -> None:
    host = url.host
    if host is None:
        return
    delay = self.delay.get(host)
    if delay is None:
        return

    key: Optional[str] = None
    while True:
        if key is None:
            key = 'throttle:{}'.format(host)
        now = time.time()
        last = self.throttle_times.get(key, 0.0)
        elapsed = now - last

        if elapsed >= delay:
            self.throttle_times[key] = now
            return

        remaining = delay - elapsed + 1

        log_string = '\nDelaying request to %s for %.2f seconds.' % (host, remaining)
        logger.debug(log_string)
        await asyncio.sleep(remaining)


class Downloader:
    def __init__(self, album_obj: AlbumItem, morsels, folder: Path, title: str, attempts: int, max_workers: int):
        self.album_obj = album_obj
        self.morsels = morsels
        self.folder = folder
        self.title = title
        self.attempts = attempts
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self.delay = {'media-files.bunkr.is': 2}
        self.throttle_times = {}

    """Changed from aiohttp exceptions caught to FailureException to allow for partial downloads."""

    @retry
    async def download_file(
            self,
            url: str,
            referral: str,
            filename: str,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL"""
        headers = {'Referer': referral, 'user-agent': user_agent}
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        try:
            async with self._semaphore:
                if yarl.URL(url).host in self.delay:
                    await throttle(self, yarl.URL(url))

                ext = '.'+filename.split('.')[-1]
                if not (ext in FILE_FORMATS['Images'] or ext in FILE_FORMATS['Videos'] or ext in FILE_FORMATS['Audio'] or ext in FILE_FORMATS['Other']):
                    resp = await session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True)
                    filename = resp.content_disposition.filename
                    filename = sanitize(filename)
                    del resp
                    if (self.folder / self.title / filename).exists():
                        return

                resume_point = 0
                complete_file = (self.folder / self.title / filename)
                temp_file = complete_file.with_suffix(complete_file.suffix + '.part')

                if temp_file.exists():
                    resume_point = temp_file.stat().st_size
                    headers['Range'] = 'bytes=%d-' % resume_point

                resp = await session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True)

                content_type = resp.headers.get('Content-Type')
                if 'text' in content_type.lower() or 'html' in content_type.lower():
                    log(f"\nServer for {url} is either down or the file no longer exists", Fore.RED)
                    return

                total = int(resp.headers.get('Content-Length', str(0))) + resume_point
                with tqdm(
                        total=total, unit_scale=True,
                        unit='B', leave=False, initial=resume_point,
                        desc=filename, disable=(not show_progress)
                ) as progress:
                    async with aiofiles.open(temp_file, mode='ab') as f:
                        async for chunk, _ in resp.content.iter_chunks():
                            await f.write(chunk)
                            progress.update(len(chunk))
            await self.rename_file(filename)
        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError, FailureException) as e:
            raise FailureException(e)

    async def rename_file(self, filename: str) -> None:
        """Rename complete file."""
        complete_file = (self.folder / self.title / filename)
        temp_file = complete_file.with_suffix(complete_file.suffix + '.part')
        if complete_file.exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
            await aiofiles.os.remove(temp_file)
        else:
            temp_file.rename(complete_file)
        logger.debug("Finished " + filename)

    async def download_and_store(
            self,
            url_tuple: Tuple,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL and store it in a file."""
        url, referral = url_tuple

        filename = url.split("/")[-1]
        filename = sanitize(filename)
        if "?v=" in url:
            filename = filename.split('v=')[0]
        if len(filename) > MAX_FILENAME_LENGTH:
            fileext = filename.split('.')[-1]
            filename = filename[:MAX_FILENAME_LENGTH] + '.' + fileext

        if (self.folder / self.title / filename).exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
        else:
            logger.debug("Working on " + url)
            try:
                await self.download_file(url, referral=referral, filename=filename,
                                         session=session, show_progress=show_progress)
            except Exception:
                logger.debug(traceback.format_exc())
                log(f"\nSkipping {filename}: likely exceeded download attempts (or ran into an error)\nRe-run program "
                    f"after exit to continue download.", Fore.WHITE)

    async def download_all(
            self,
            album_obj: AlbumItem,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the data from all given links and store them into corresponding files."""
        coros = [self.download_and_store(url_object, session, show_progress)
                 for url_object in album_obj.link_pairs]
        for func in tqdm(asyncio.as_completed(coros), total=len(coros), desc=self.title, unit='FILES'):
            await func

    async def download_content(
            self,
            show_progress: bool = True
    ) -> None:
        """Download the content of all links and save them as files."""
        (self.folder / self.title).mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(self.morsels)
            await self.download_all(self.album_obj, session, show_progress=show_progress)


def simple_cookies(cookies):
    morsels = {}
    for cookie in cookies:
        # https://docs.python.org/3/library/http.cookies.html#morsel-objects
        morsel = http.cookies.Morsel()
        morsel.set(cookie["name"], cookie["value"], cookie["value"])
        if "domain" in cookie:
            morsel["domain"] = cookie["domain"]
        if "httpOnly" in cookie:
            morsel["httponly"] = cookie["httpOnly"]
        if "path" in cookie:
            morsel["path"] = cookie["path"]
        if "secure" in cookie:
            morsel["secure"] = cookie["secure"]

        morsels[cookie["name"]] = morsel
    return morsels


def get_downloaders(Cascade: CascadeItem, folder: Path, attempts: int, threads: int) -> list[Downloader]:
    """Get a list of downloaders for each supported type of URLs.
    We shouldn't just assume that each URL will have the same netloc as
    the first one, so we need to classify them one by one, sort them to
    corresponding netloc URLs and create downloaders separately for individual
    netloc URLs they support.
    """

    downloaders = []
    morsels = simple_cookies(Cascade.cookies.cookies)

    for domain, domain_obj in Cascade.domains.items():
        max_workers = threads if threads != 0 else multiprocessing.cpu_count()
        if 'bunkr' in domain:
            max_workers = 2 if (max_workers > 2) else max_workers
        for title, album_obj in domain_obj.albums.items():
            downloader = Downloader(album_obj, morsels=morsels, title=title, folder=folder,
                                    attempts=attempts, max_workers=max_workers)
            downloaders.append(downloader)
    return downloaders
