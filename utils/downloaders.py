import asyncio
import http
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Type, TypeVar, Union, cast, Dict
from urllib.parse import urljoin
import aiofiles
import aiofiles.os
import aiohttp
import aiohttp.client_exceptions
from requests.structures import CaseInsensitiveDict
from tqdm import tqdm
import logging
from colorama import Fore, Style
from sanitize_filename import sanitize
import ssl
import certifi
from http.cookies import SimpleCookie
import settings
import multiprocessing


asyncio.get_event_loop()
logger = logging.getLogger(__name__)

T = TypeVar("T")
T_Func = TypeVar("T_Func", bound=Callable)

MAX_FILENAME_LENGTH = 100
FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.gif', '.webp', '.jpe', '.svg',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg',
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a'
    }
}


def log(text, style):
    # Log function for printing to command line
    print(style + str(text) + Style.RESET_ALL)


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""
    pass


def retry(
        attempts: int,
        timeout: Union[int, float] = 0,
        exceptions: Type[Exception] = Exception
) -> Callable:
    def inner(func: T_Func) -> T_Func:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            times_tried = 1
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    # logger.exception(exc)
                    if times_tried >= attempts:
                        logger.exception(f'Raised {exc} exceeded times_tried')
                        raise exc
                    times_tried += 1
                    await asyncio.sleep(timeout)

        return cast(T_Func, wrapper)

    return inner


class Downloader:
    def __init__(self, links: List[List[str]], morsels, folder: Path, title: str, max_workers: int):
        self.links = links
        self.morsels = morsels
        self.folder = folder
        self.title = title
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)

    @staticmethod
    def bunkr_parse(url: str) -> str:
        """Fix the URL for bunkr.is and construct the headers."""
        extension = '.' + url.split('.')[-1]
        if extension.lower() in FILE_FORMATS['Videos']:
            changed_url = url.replace('cdn.bunkr', 'media-files.bunkr').split('/')
            changed_url = ''.join(map(lambda x: urljoin('/', x), changed_url))
            return changed_url
        if extension.lower() in FILE_FORMATS['Images']:
            changed_url = url.replace('i.bunkr', 'cdn.bunkr')
            return changed_url
        return url

    """Changed from aiohttp exceptions caught to FailureException to allow for partial downloads."""
    @retry(attempts=settings.download_attempts, timeout=4, exceptions=FailureException)
    async def download_file(
            self,
            url: str,
            referal: str,
            filename: str,
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL"""
        temp_file = (self.folder / self.title / filename).with_suffix(".download")
        resume_point = 0
        downloaded = bytearray()
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36'

        if 'bunkr' in url:
            url = self.bunkr_parse(url)

        headers = {'Referer': referal, 'user-agent': user_agent}

        if temp_file.exists():
            resume_point = temp_file.stat().st_size
            headers['Range'] = 'bytes=%d-' % resume_point

        try:
            async with self._semaphore:
                resp = await session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True)
                total = int(resp.headers.get('Content-Length', 0)) + resume_point
                with tqdm(
                    total=total, unit_scale=True,
                    unit='B', leave=False, initial=resume_point,
                    desc=filename, disable=(not show_progress)
                ) as progress:
                    async for chunk, _ in resp.content.iter_chunks():
                        downloaded.extend(chunk)
                        progress.update(len(chunk))
            await self.write_partial(temp_file, downloaded)

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError) as e:
            await self.write_partial(temp_file, downloaded)
            raise FailureException(e)

    async def write_partial(self, filename: Path, downloaded: bytearray) -> None:
        """Store partial or full data into file"""
        async with aiofiles.open(filename, mode='ab') as f:
            await f.write(downloaded)

    async def rename_file(self, filename: str) -> None:
        """Rename complete file."""
        complete_file = (self.folder / self.title / filename)
        temp_file = complete_file.with_suffix(".download")
        if complete_file.exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
            await aiofiles.os.remove(temp_file)
        else:
            temp_file.rename(complete_file)
        logger.debug("Finished " + filename)

    async def download_and_store(
            self,
            url_object: list,
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL and store it in a file."""
        url = url_object[0]
        referal = url_object[1]

        filename = sanitize(url.split("/")[-1])
        if "?v=" in url:
            filename = filename.split('v=')[0]
        if len(filename) > MAX_FILENAME_LENGTH:
            fileext = filename.split('.')[-1]
            filename = filename[:MAX_FILENAME_LENGTH]+'.'+fileext

        if (self.folder / self.title / filename).exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
        else:
            logger.debug("Working on " + url)
            try:
                await self.download_file(url, referal=referal, filename=filename, session=session, headers=headers, show_progress=show_progress)
                await self.rename_file(filename)
            except Exception as e:
                print(e)
                log(f"\nSkipping {filename}: likely exceeded download attempts\nRe-run program after exit to continue download.", Fore.WHITE)

    async def download_all(
            self,
            links: Iterable[List[str]],
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the data from all given links and store them into corresponding files."""
        coros = [self.download_and_store(
            link, session, headers, show_progress) for link in links]
        for func in tqdm(asyncio.as_completed(coros), total=len(coros), desc=self.title, unit='FILES'):
            await func

    async def download_content(
            self,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the content of all links and save them as files."""
        (self.folder / self.title).mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            session.cookie_jar.update_cookies(self.morsels)
            await self.download_all(self.links, session, headers=headers, show_progress=show_progress)


def simple_cookies(cookies):
    morsels = {}
    for cookie in cookies:
        # https://docs.python.org/3/library/http.cookies.html#morsel-objects
        morsel = http.cookies.Morsel()
        morsel.set(cookie["name"], cookie["value"], cookie["value"])
        morsel["domain"] = cookie["domain"]
        morsel["httponly"] = cookie["httpOnly"]
        morsel["path"] = cookie["path"]
        morsel["secure"] = cookie["secure"]

        morsels[cookie["name"]] = morsel
    return morsels


def get_downloaders(urls: Dict[str, Dict[str, List[str]]], cookies: Iterable[str], folder: Path) -> List[Downloader]:
    """Get a list of downloaders for each supported type of URLs.

    We shouldn't just assume that each URL will have the same netloc as
    the first one, so we need to classify them one by one, sort them to
    corresponding netloc URLs and create downloaders separately for individual
    netloc URLs they support.
    """

    downloaders = []
    morsels = simple_cookies(cookies)

    for domain, url_object in urls.items():
        max_workers = settings.threads if settings.threads != 0 else multiprocessing.cpu_count()
        if 'bunkr' in domain:
            max_workers = 2 if (max_workers > 2) else max_workers
        for title, urls in url_object.items():
            downloader = Downloader(urls, morsels=morsels, title=title, folder=folder, max_workers=max_workers)
            downloaders.append(downloader)
    return downloaders
