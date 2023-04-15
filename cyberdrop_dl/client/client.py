from __future__ import annotations

import asyncio
import json
import logging
import ssl
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiofiles
import aiohttp
import certifi
from bs4 import BeautifulSoup
from tqdm import tqdm
from yarl import URL

from ..base_functions.base_functions import adjust, logger
from ..base_functions.error_classes import DownloadFailure, InvalidContentTypeFailure
from ..downloader.downloader_utils import CustomHTTPStatus
from ..downloader.progress_definitions import file_progress
from .rate_limiting import AsyncRateLimiter, throttle

if TYPE_CHECKING:
    from pathlib import Path

    from rich.progress import TaskID

    from ..base_functions.data_classes import MediaItem


class Client:
    """Creates a 'client' that can be referenced by scraping or download sessions"""
    def __init__(self, ratelimit: int, throttle: int, secure: bool, connect_timeout: int):
        self.connect_timeout = connect_timeout
        self.ratelimit = ratelimit
        self.throttle = throttle
        self.simultaneous_session_limit = asyncio.Semaphore(50)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0'
        self.verify_ssl = secure
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if secure else False
        self.cookies = aiohttp.CookieJar(quote_cookie=False)


class ScrapeSession:
    """AIOHTTP operations for scraping"""
    def __init__(self, client: Client) -> None:
        self.client = client
        self.rate_limiter = AsyncRateLimiter(self.client.ratelimit)
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=5 * 60, connect=self.client.connect_timeout, sock_read=30)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True, cookie_jar=self.client.cookies, timeout=self.timeouts)

    async def get_BS4(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    content_type = response.headers.get('Content-Type')
                    if 'text' in content_type.lower() or 'html' in content_type.lower():
                        text = await response.text()
                        soup = BeautifulSoup(text, 'html.parser')
                        return soup
                    else:
                        raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")

    async def get_BS4_and_url(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'html.parser')
                    return soup, URL(response.url)

    async def get_json(self, url: URL, params: dict = None):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context, params=params) as response:
                    return json.loads(await response.content.read())

    async def get_text(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    text = await response.text()
                    return text

    async def post(self, url: URL, data: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context) as response:
                    content = json.loads(await response.content.read())
                    return content

    async def get_no_resp(self, url: URL, headers: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context):
                    pass

    async def post_data_no_resp(self, url: URL, data: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context):
                    pass

    async def exit_handler(self):
        try:
            await self.client_session.close()
        except Exception:
            logging.debug("Failed to close session.")


class DownloadSession:
    """AIOHTTP operations for downloading"""
    def __init__(self, client: Client):
        self.client = client
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=5 * 60, connect=self.client.connect_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True, cookie_jar=self.client.cookies, timeout=self.timeouts)
        self.throttle_times = {}

        self.bunkr_maintenance = [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"), URL("https://bnkr.b-cdn.net/maintenance.mp4")]

    async def download_file(self, media: MediaItem, file: Path, current_throttle: int, resume_point: int,
                            proxy: str, headers: dict, file_task: TaskID):
        headers['Referer'] = str(media.referer)
        headers['user-agent'] = self.client.user_agent
        await throttle(self, current_throttle, media.url.host)
        async with self.client_session.get(media.url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True, proxy=proxy) as resp:
            content_type = resp.headers.get('Content-Type')
            if not content_type:
                raise DownloadFailure(code=CustomHTTPStatus.IM_A_TEAPOT, message="No content-type in response header")
            if resp.url in self.bunkr_maintenance:
                raise DownloadFailure(code=HTTPStatus.SERVICE_UNAVAILABLE, message="Bunkr under maintenance")
            if 'text' in content_type.lower() or 'html' in content_type.lower():
                logger.debug("Server for %s is experiencing issues, you are being ratelimited, or cookies have expired", str(media.url))
                raise DownloadFailure(code=CustomHTTPStatus.IM_A_TEAPOT, message="Unexpectedly got text as response")

            total = int(resp.headers.get('Content-Length', str(0))) + resume_point
            file.parent.mkdir(parents=True, exist_ok=True)

            file_progress.update(file_task, total=total)
            file_progress.advance(file_task, resume_point)

            async with aiofiles.open(file, mode='ab') as f:
                async for chunk, _ in resp.content.iter_chunks():
                    await asyncio.sleep(0)
                    await f.write(chunk)
                    file_progress.advance(file_task, len(chunk))

    async def old_download_file(self, media: MediaItem, file: Path, current_throttle: int, resume_point: int,
                                proxy: str, headers: dict):
        headers['Referer'] = str(media.referer)
        headers['user-agent'] = self.client.user_agent
        await throttle(self, current_throttle, media.url.host)
        async with self.client_session.get(media.url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True, proxy=proxy) as resp:
            content_type = resp.headers.get('Content-Type')
            if not content_type:
                raise DownloadFailure(code=CustomHTTPStatus.IM_A_TEAPOT, message="No content-type in response header")
            if resp.url in self.bunkr_maintenance:
                raise DownloadFailure(code=HTTPStatus.SERVICE_UNAVAILABLE, message="Bunkr under maintenance")
            if 'text' in content_type.lower() or 'html' in content_type.lower():
                logger.debug("Server for %s is experiencing issues, you are being ratelimited, or cookies have expired", str(media.url))
                raise DownloadFailure(code=CustomHTTPStatus.IM_A_TEAPOT, message="Unexpectedly got text as response")

            total = int(resp.headers.get('Content-Length', str(0))) + resume_point
            file.parent.mkdir(parents=True, exist_ok=True)

            task_description = await adjust(f"{media.url.host}: {media.filename}")

            with tqdm(total=total, unit_scale=True, unit='B', leave=False, initial=resume_point,
                      desc=task_description) as progress:
                async with aiofiles.open(file, mode='ab') as f:
                    async for chunk, _ in resp.content.iter_chunks():
                        await asyncio.sleep(0)
                        await f.write(chunk)
                        progress.update(len(chunk))

    async def get_filesize(self, url: URL, referer: str, current_throttle: int):
        headers = {'Referer': referer, 'user-agent': self.client.user_agent}
        await throttle(self, current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True) as resp:
            total_size = int(resp.headers.get('Content-Length', str(0)))
            return total_size

    async def exit_handler(self):
        try:
            await self.client_session.close()
        except Exception:
            logging.debug("Failed to close session.")
