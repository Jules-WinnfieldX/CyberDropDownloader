import asyncio
import json
import logging
import ssl
from pathlib import Path
import xml.etree.ElementTree as ET

import aiofiles
from bs4 import BeautifulSoup
from yarl import URL

import aiohttp
import certifi
from tqdm import tqdm

from .rate_limiting import AsyncRateLimiter, throttle
from ..base_functions.base_functions import logger, FailureException
from ..base_functions.data_classes import FileLock


class Client:
    def __init__(self, ratelimit: int, throttle: int):
        self.ratelimit = ratelimit
        self.throttle = throttle
        self.simultaneous_session_limit = asyncio.Semaphore(50)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.cookies = aiohttp.CookieJar(quote_cookie=False)


class Session:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.rate_limiter = AsyncRateLimiter(self.client.ratelimit)
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(5 * 60, 30)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True, cookie_jar=self.client.cookies, timeout=self.timeouts)

    async def get_BS4(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'html.parser')
                    return soup

    async def get_text(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    text = await response.text()
                    return text

    async def get_json(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    content = json.loads(await response.content.read())
                    return content

    async def get_xml(self, url: URL):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, ssl=self.client.ssl_context) as response:
                    text = await response.content.read()
                    xmlTree = ET.fromstring(text)
                    return xmlTree

    async def post_no_resp(self, url: URL, headers: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context) as response:
                    pass

    async def post_data_no_resp(self, url: URL, data: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context) as response:
                    pass

    async def post(self, url: URL, data: dict):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                async with self.client_session.post(url, data=data, headers=self.headers, ssl=self.client.ssl_context) as response:
                    content = json.loads(await response.content.read())
                    return content

    async def exit_handler(self):
        try:
            await self.client_session.close()
        except Exception as e:
            logging.debug(f"Failed to close session.")


class DownloadSession:
    def __init__(self, client: Client, conn_timeout: int):
        self.client = client
        self.headers = {"user-agent": client.user_agent}
        self.timeouts = aiohttp.ClientTimeout(5*60, conn_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=self.client.cookies, timeout=self.timeouts)
        self.throttle_times = {}

    async def get_filename(self, url: URL, referer: str, current_throttle: int):
        headers = {'Referer': referer, 'user-agent': self.client.user_agent}
        await throttle(self, current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True) as resp:
            filename = resp.content_disposition.filename
            return filename

    async def get_filesize(self, url: URL, referer: str, current_throttle: int):
        headers = {'Referer': referer, 'user-agent': self.client.user_agent}
        await throttle(self, current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True) as resp:
            total_size = int(resp.headers.get('Content-Length', str(0)))
            return total_size

    async def get_content_type(self, url: URL, referer: str, current_throttle: int):
        headers = {'Referer': referer, 'user-agent': self.client.user_agent}
        await throttle(self, current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True) as resp:
            content_type = resp.headers.get('Content-Type')
            return content_type.lower()

    async def download_file(self, url: URL, referer: str, current_throttle: int, range_num: str, original_filename: str,
                            filename: str, temp_file: str, resume_point: int, show_progress: bool,
                            File_Lock: FileLock, folder: Path, title: str, proxy: str):
        headers = {'Referer': referer, 'user-agent': self.client.user_agent}
        if range_num:
            headers['Range'] = range_num
        await throttle(self, current_throttle, url.host)
        async with self.client_session.get(url, headers=headers, ssl=self.client.ssl_context,
                                           raise_for_status=True, proxy=proxy) as resp:
            content_type = resp.headers.get('Content-Type')
            if 'text' in content_type.lower() or 'html' in content_type.lower():
                logger.debug("Server for %s is experiencing issues, or you are being ratelimited", str(url))
                logger.debug("Content received: " + content_type.lower())
                await File_Lock.remove_lock(original_filename)
                raise FailureException(code=resp.status, message="Unexpectedly got text as response", rescrape=True)

            total = int(resp.headers.get('Content-Length', str(0))) + resume_point
            (folder / title).mkdir(parents=True, exist_ok=True)

            with tqdm(total=total, unit_scale=True, unit='B', leave=False, initial=resume_point, desc=filename,
                      disable=(not show_progress)) as progress:
                async with aiofiles.open(temp_file, mode='ab') as f:
                    async for chunk, _ in resp.content.iter_chunks():
                        await asyncio.sleep(0)
                        await f.write(chunk)
                        progress.update(len(chunk))
