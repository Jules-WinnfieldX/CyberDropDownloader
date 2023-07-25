from __future__ import annotations

import asyncio
import functools
import json
import logging
import ssl
import time
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, Optional, Tuple

import aiofiles
import aiohttp
import certifi
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from multidict import CIMultiDictProxy
from pathlib import Path
from tqdm import tqdm
from yarl import URL

from ..base_functions.base_functions import logger, FILE_FORMATS
from ..base_functions.error_classes import DownloadFailure, InvalidContentTypeFailure
from ..downloader.downloader_utils import CustomHTTPStatus
from ..downloader.progress_definitions import ProgressMaster, adjust_title

if TYPE_CHECKING:
    from rich.progress import TaskID

    from ..base_functions.data_classes import MediaItem


def scrape_limit(func):
    """Wrapper handles limits for scrape session"""

    async def wrapper(self, *args, **kwargs):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                return await func(self, *args, **kwargs)

    return wrapper


class Client:
    """Creates a 'client' that can be referenced by scraping or download sessions"""
    def __init__(self, ratelimit: int, throttle: float, secure: bool, connect_timeout: int, read_timeout: int,
                 user_agent: str):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.ratelimit = ratelimit
        self.throttle = throttle
        self.simultaneous_session_limit = asyncio.Semaphore(50)
        self.user_agent = user_agent
        self.verify_ssl = secure
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if secure else False
        self.cookies = aiohttp.CookieJar(quote_cookie=False)


class ScrapeSession:
    """AIOHTTP operations for scraping"""
    def __init__(self, client: Client) -> None:
        self.client = client
        self.rate_limiter = AsyncLimiter(self.client.ratelimit, 1)
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=self.client.connect_timeout + 60,
                                              connect=self.client.connect_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=self.client.cookies, timeout=self.timeouts)

    @scrape_limit
    async def get_BS4(self, url: URL) -> BeautifulSoup:
        async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if not any(s in content_type.lower() for s in ("html", "text")):
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")
            text = await response.text()
            return BeautifulSoup(text, 'html.parser')

    @scrape_limit
    async def get_BS4_and_url(self, url: URL) -> Tuple[BeautifulSoup, URL]:
        async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            return soup, URL(response.url)

    @scrape_limit
    async def get_json(self, url: URL, params: Optional[Dict] = None, headers_inc: Optional[Dict] = None) -> Dict:
        headers = {**self.headers, **headers_inc} if headers_inc else self.headers
        async with self.client_session.get(url, ssl=self.client.ssl_context, params=params, headers=headers) as response:
            return json.loads(await response.content.read())

    @scrape_limit
    async def get_json_with_headers(self, url: URL, params: Optional[Dict] = None,
                                    headers_inc: Optional[Dict] = None) -> tuple[Any, CIMultiDictProxy[str]]:
        headers = {**self.headers, **headers_inc} if headers_inc else self.headers
        async with self.client_session.get(url, ssl=self.client.ssl_context, params=params, headers=headers) as response:
            content = await response.content.read()
            return json.loads(content), response.headers

    @scrape_limit
    async def get_text(self, url: URL) -> str:
        async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
            return await response.text()

    @scrape_limit
    async def post(self, url: URL, data: Dict) -> Dict:
        async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context) as response:
            return json.loads(await response.content.read())

    @scrape_limit
    async def post_with_auth(self, url: URL, data: Dict, auth: aiohttp.BasicAuth) -> Dict:
        async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context, auth=auth) as response:
            return json.loads(await response.content.read())

    @scrape_limit
    async def get_no_resp(self, url: URL, headers: Dict) -> None:
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context):
            pass

    @scrape_limit
    async def post_data_no_resp(self, url: URL, data: Dict) -> None:
        async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context):
            pass

    async def exit_handler(self) -> None:
        try:
            await self.client_session.close()
        except Exception:
            logging.debug("Failed to close session.")


class DownloadSession:
    """AIOHTTP operations for downloading"""
    def __init__(self, client: Client):
        self.client = client
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=self.client.read_timeout + self.client.connect_timeout,
                                              connect=self.client.connect_timeout, sock_read=self.client.read_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=self.client.cookies, timeout=self.timeouts)
        self.throttle_times: Dict[str, float] = {}
        self.bunkr_maintenance = [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"), URL("https://bnkr.b-cdn.net/maintenance.mp4")]

    async def _append_content(self, file: Path, content: aiohttp.StreamReader,
                              update_progress: functools.partial | Callable[[int], Optional[bool]]) -> None:
        file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file, mode='ab') as f:
            async for chunk, _ in content.iter_chunks():
                await asyncio.sleep(0)
                await f.write(chunk)
                if isinstance(update_progress, functools.partial):
                    await update_progress(len(chunk))
                else:
                    update_progress(len(chunk))

    async def _download(self, media: MediaItem, current_throttle: float, proxy: str, headers: Dict,
                        save_content: Callable[[aiohttp.StreamReader], Coroutine[Any, Any, None]], file: Path) -> None:
        headers['Referer'] = str(media.referer)
        headers['user-agent'] = self.client.user_agent

        assert media.url.host is not None
        await self._throttle(current_throttle, media.url.host)

        async with self.client_session.get(media.url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True, proxy=proxy) as resp:
            content_type = resp.headers.get('Content-Type')
            if not content_type:
                raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="No content-type in response header")
            if resp.url in self.bunkr_maintenance:
                raise DownloadFailure(status=HTTPStatus.SERVICE_UNAVAILABLE, message="Bunkr under maintenance")
            if "imgur.com/removed" in str(resp.url):
                raise DownloadFailure(status=HTTPStatus.NOT_FOUND, message="Imgur image has been removed")

            extname = Path(media.filename).suffix.lower()
            if any(s in content_type.lower() for s in ('html', 'text')) and extname not in FILE_FORMATS['Text']:
                logger.debug("Server for %s is experiencing issues, you are being ratelimited, or cookies have expired", media.url)
                raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="Unexpectedly got text as response")

            if resp.status != HTTPStatus.PARTIAL_CONTENT:
                if file.is_file():
                    file.unlink()

            await save_content(resp.content)

    async def _throttle(self, delay: float, host: str) -> None:
        """Throttles requests to domains by a parameter amount of time"""
        if delay is None or delay == 0:
            return

        key = f'throttle:{host}'
        while True:
            now = time.time()
            last = self.throttle_times.get(key, 0.0)
            elapsed = now - last

            if elapsed >= delay:
                self.throttle_times[key] = now
                return

            remaining = delay - elapsed + 0.1
            await asyncio.sleep(remaining)

    async def download_file(self, Progress_Master: ProgressMaster, media: MediaItem, file: Path,
                            current_throttle: float, resume_point: int, proxy: str, headers: Dict,
                            file_task: TaskID) -> None:

        async def save_content(content: aiohttp.StreamReader) -> None:
            await Progress_Master.FileProgress.advance_file(file_task, resume_point)
            await self._append_content(file, content, functools.partial(Progress_Master.FileProgress.advance_file, file_task))

        await self._download(media, current_throttle, proxy, headers, save_content, file)

    async def old_download_file(self, media: MediaItem, file: Path, current_throttle: float, resume_point: int,
                                proxy: str, headers: Dict, size: int) -> None:

        async def save_content(content: aiohttp.StreamReader) -> None:
            task_description = adjust_title(f"{media.url.host}: {media.filename}")
            with tqdm(total=size + resume_point, unit_scale=True, unit='B', leave=False,
                      initial=resume_point, desc=task_description) as progress:
                await self._append_content(file, content, lambda chunk_len: progress.update(chunk_len))

        await self._download(media, current_throttle, proxy, headers, save_content, file)

    async def get_filesize(self, url: URL, referer: str, current_throttle: float, headers: Dict) -> int:
        headers['Referer'] = referer
        headers['user-agent'] = self.client.user_agent

        assert url.host is not None
        await self._throttle(current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=False) as resp:
            if resp.status > 206:
                if "Server" in resp.headers:
                    if resp.headers["Server"] == "ddos-guard":
                        raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="DDoS-Guard detected, unable to download")
                raise DownloadFailure(status=resp.status, message=f"Unexpected status code {resp.status} from {url}")
            return int(resp.headers.get('Content-Length', '0'))

    async def exit_handler(self) -> None:
        try:
            await self.client_session.close()
        except Exception:
            logging.debug("Failed to close session.")
