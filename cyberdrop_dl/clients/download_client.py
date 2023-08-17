from __future__ import annotations

import asyncio
import copy
import functools
from enum import IntEnum
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiofiles
import aiohttp
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import DownloadFailure
from cyberdrop_dl.utils.utilities import FILE_FORMATS

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Dict, Callable, Coroutine, Any

    from cyberdrop_dl.managers.client_manager import ClientManager
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


class CustomHTTPStatus(IntEnum):
    WEB_SERVER_IS_DOWN = 521
    IM_A_TEAPOT = 418


async def is_4xx_client_error(status_code: int) -> bool:
    """Checks whether the HTTP status code is 4xx client error"""
    return HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR


class DownloadClient:
    """AIOHTTP operations for downloading"""
    def __init__(self, client_manager: ClientManager):
        self.client_manager = client_manager
        self.headers = {"user-agent": client_manager.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=client_manager.read_timeout + client_manager.connection_timeout,
                                              connect=client_manager.connection_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=client_manager.cookies, timeout=self.timeouts)
        self.throttle_times: Dict[str, float] = {"user_agent": client_manager.user_agent}
        self.bunkr_maintenance = [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"),
                                  URL("https://bnkr.b-cdn.net/maintenance.mp4")]

    async def get_filesize(self, media_item: MediaItem) -> int:
        """Returns the file size of the media item"""
        headers = copy.deepcopy(self.headers)
        headers['Referer'] = media_item.referer

        async with self.client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                           raise_for_status=False) as resp:
            if resp.status > 206:
                if "Server" in resp.headers:
                    if resp.headers["Server"] == "ddos-guard":
                        raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT,
                                              message="DDoS-Guard detected, unable to download")
                raise DownloadFailure(status=resp.status, message=f"Unexpected status code {resp.status} from {media_item.url}")
            return int(resp.headers.get('Content-Length', '0'))

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def _download(self, media_item: MediaItem, headers_inc: Dict,
                        save_content: Callable[[aiohttp.StreamReader], Coroutine[Any, Any, None]], file: Path) -> None:
        headers = copy.deepcopy(self.headers)
        headers['Referer'] = media_item.referer
        headers.update(headers_inc)

        async with self.client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                           raise_for_status=True, proxy=self.client_manager.proxy) as resp:
            content_type = resp.headers.get('Content-Type')
            if not content_type:
                raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="No content-type in response header")
            if resp.url in self.bunkr_maintenance:
                raise DownloadFailure(status=HTTPStatus.SERVICE_UNAVAILABLE, message="Bunkr under maintenance")
            if "imgur.com/removed" in str(resp.url):
                raise DownloadFailure(status=HTTPStatus.NOT_FOUND, message="Imgur image has been removed")

            ext = Path(media_item.filename).suffix.lower()
            if any(s in content_type.lower() for s in ('html', 'text')) and ext not in FILE_FORMATS['Text']:
                raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="Unexpectedly got text as response")

            if resp.status != HTTPStatus.PARTIAL_CONTENT:
                if file.is_file():
                    file.unlink()

            await save_content(resp.content)

    async def _append_content(self, file: Path, content: aiohttp.StreamReader, update_progress: functools.partial) -> None:
        file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file, mode='ab') as f:
            async for chunk, _ in content.iter_chunks():
                await asyncio.sleep(0)
                await f.write(chunk)
                if isinstance(update_progress, functools.partial):
                    await update_progress(len(chunk))
                else:
                    update_progress(len(chunk))

    async def download_file(self, manager: Manager, media_item: MediaItem, partial_file: Path, headers: Dict) -> None:

        async def save_content(content: aiohttp.StreamReader) -> None:
            await self._append_content(partial_file, content, functools.partial())

        await self._download(media_item, headers, save_content, partial_file)

