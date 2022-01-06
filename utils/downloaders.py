import asyncio
import itertools
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type, TypeVar, Union, cast, Dict
from urllib.parse import urljoin, urlparse
import aiofiles
import aiohttp
import aiohttp.client_exceptions
from requests.structures import CaseInsensitiveDict
from tqdm import tqdm
import logging
from sanitize_filename import sanitize
import ssl
import certifi

logger = logging.getLogger(__name__)

T = TypeVar("T")
T_Func = TypeVar("T_Func", bound=Callable)


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


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""
    pass


def retry(
        attempts: int,
        timeout: Union[int, float] = 0,
        exceptions: Iterable[Type[Exception]] = (Exception,)
) -> Callable:
    def inner(func: T_Func) -> T_Func:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            times_tried = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    # logger.exception(exc)
                    if times_tried > attempts:
                        logger.exception(f'Raised {exc} exceeded times_tried')
                        raise exc
                    times_tried += 1
                    await asyncio.sleep(timeout)

        return cast(T_Func, wrapper)

    return inner


class Downloader:
    def __init__(self, links: List[str], folder: Path, title: str, max_workers: int):
        self.links = links
        self.folder = folder
        self.title = title
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)

    """Changed from aiohttp exceptions caught to FailureException to allow for partial downloads."""
    @retry(attempts=10, timeout=4, exceptions=FailureException)
    async def download_file(
            self,
            url: str,
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

        if temp_file.exists():
            resume_point = temp_file.stat().st_size
            if headers:
                headers['Range'] = 'bytes=%d-' % resume_point
            else:
                headers = {'Range': 'bytes=%d-' % resume_point}
        try:
            async with self._semaphore:
                resp = await session.get(url, headers=headers, ssl=ssl_context)
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

        temp_file.rename(complete_file)
        logger.debug("Finished " + filename)

    async def download_and_store(
            self,
            url: str,
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL and store it in a file."""
        filename = sanitize(url.split("/")[-1])
        if (self.folder / self.title / filename).exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
        else:
            logger.debug("Working on " + url)
            await self.download_file(url, filename=filename, session=session, headers=headers, show_progress=show_progress)
            await self.rename_file(filename)

    async def download_all(
            self,
            links: Iterable[str],
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
            await self.download_all(self.links, session, headers=headers, show_progress=show_progress)


class BunkrDownloader(Downloader):
    @staticmethod
    def bunkr_parse(url: str) -> str:
        """Fix the URL for bunkr.is and construct the headers."""
        extension = '.' + url.split('.')[-1]
        if extension.lower() in FILE_FORMATS['Videos']:
            changed_url = url.replace('cdn.bunkr', 'stream.bunkr').split('/')
            changed_url.insert(3, 'v')
            changed_url = ''.join(map(lambda x: urljoin('/', x), changed_url))
            return changed_url.replace('/v/', '/d/')
        if extension.lower() in FILE_FORMATS['Images']:
            changed_url = url.replace('cdn.bunkr', 'i.bunkr')
            return changed_url
        return url

    @staticmethod
    def pairwise_skipping(it: Iterable[T], chunk_size: int) -> Tuple[T, ...]:
        """Iterate over tuples of the iterable of size `chunk_size` at a time."""
        split_it = [it[i:i+chunk_size] for i in range(0, len(it), chunk_size)]
        return map(tuple, split_it)

    async def download_file(
            self,
            url: str,
            filename: str,
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> bytearray:
        url = self.bunkr_parse(url)
        return await super().download_file(url, filename=filename, session=session, headers=headers, show_progress=show_progress)

    async def download_all(
            self,
            links: Iterable[str],
            session: aiohttp.ClientSession,
            headers: Optional[CaseInsensitiveDict] = None,
            show_progress: bool = True
    ) -> None:
        """Download the data from all given links and store them into corresponding files.

        We override this method to only make requests to 2 links at a time,
        since bunkr.is can't handle more traffic and causes errors.
        """
        chunked_links = self.pairwise_skipping(self.links, chunk_size=2)
        for links in chunked_links:
            await super().download_all(links, session, headers=headers, show_progress=show_progress)


def get_downloaders(urls: Dict[str, Dict[str, List[str]]], folder: Path, max_workers: int) -> List[Downloader]:
    """Get a list of downloaders for each supported type of URLs.

    We shouldn't just assume that each URL will have the same netloc as
    the first one, so we need to classify them one by one, sort them to
    corresponding netloc URLs and create downloaders separately for individual
    netloc URLs they support.
    """
    mapping = {
        'cyberdrop.me': Downloader,
        'bunkr.is': BunkrDownloader,
        'pixl.is': Downloader,
        'putme.ga': Downloader,
        'cyberdrop.to': Downloader
    }

    downloaders = []
    for domain, url_object in urls.items():
        if domain not in mapping:
            logging.error('Invalid URL!')
            raise ValueError('Invalid URL!')
        for title, urls in url_object.items():
            downloader = mapping[domain](urls, title=title, folder=folder, max_workers=max_workers)
            downloaders.append(downloader)
    return downloaders
