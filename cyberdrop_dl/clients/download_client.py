from __future__ import annotations

import asyncio
import copy
from http import HTTPStatus
from functools import wraps, partial
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import aiohttp
from aiohttp import ClientSession
from rich.progress import TaskID

from cyberdrop_dl.clients.errors import DownloadFailure, InvalidContentTypeFailure
from cyberdrop_dl.utils.utilities import CustomHTTPStatus, FILE_FORMATS

if TYPE_CHECKING:
    from typing import Dict, Callable, Coroutine, Any

    from cyberdrop_dl.managers.client_manager import ClientManager
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


async def is_4xx_client_error(status_code: int) -> bool:
    """Checks whether the HTTP status code is 4xx client error"""
    if isinstance(status_code, str):
        return True
    return HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR


def limiter(func):
    """Wrapper handles limits for download session"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        domain_limiter = await self.client_manager.get_rate_limiter(args[0])
        await asyncio.sleep(await self.client_manager.get_downloader_spacer(args[0]))
        await self._global_limiter.acquire()
        await domain_limiter.acquire()

        async with aiohttp.ClientSession(headers=self._headers, raise_for_status=False,
                                         cookie_jar=self.client_manager.cookies, timeout=self._timeouts) as client:
            kwargs['client_session'] = client
            return await func(self, *args, **kwargs)
    return wrapper


class DownloadClient:
    """AIOHTTP operations for downloading"""
    def __init__(self, client_manager: ClientManager):
        self.client_manager = client_manager
        self._headers = {"user-agent": client_manager.user_agent}
        self._timeouts = aiohttp.ClientTimeout(total=client_manager.read_timeout + client_manager.connection_timeout,
                                               connect=client_manager.connection_timeout)
        self._global_limiter = self.client_manager.global_rate_limiter

    @limiter
    async def get_filesize(self, media_item: MediaItem, client_session: ClientSession) -> int:
        """Returns the file size of the media item"""
        headers = copy.deepcopy(self._headers)
        headers['Referer'] = str(media_item.referer)

        async with client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as resp:
            await self.client_manager.check_http_status(resp)
            return int(resp.headers.get('Content-Length', '0'))

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @limiter
    async def _download(self, domain: str, manager: Manager, media_item: MediaItem, headers_inc: Dict,
                        save_content: Callable[[aiohttp.StreamReader], Coroutine[Any, Any, None]], file: Path,
                        file_task: TaskID, client_session: ClientSession) -> None:
        """Downloads a file"""
        headers = copy.deepcopy(self._headers)
        headers['Referer'] = str(media_item.referer)
        headers.update(headers_inc)

        await asyncio.sleep(self.client_manager.download_delay)

        async with client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as resp:
            await self.client_manager.check_http_status(resp, download=True)
            content_type = resp.headers.get('Content-Type')
            ext = Path(media_item.filename).suffix.lower()
            if any(s in content_type.lower() for s in ('html', 'text')) and ext not in FILE_FORMATS['Text']:
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting other")

            if resp.status != HTTPStatus.PARTIAL_CONTENT and file.is_file():
                await manager.progress_manager.file_progress.advance_file(file_task, -file.stat().st_size)
                file.unlink()

            await save_content(resp.content)

    async def _append_content(self, file: Path, content: aiohttp.StreamReader,
                              update_progress: partial) -> None:
        """Appends content to a file"""
        if not await self.client_manager.manager.download_manager.check_free_space():
            raise DownloadFailure(status="No Free Space", message="Not enough free space")

        file.parent.mkdir(parents=True, exist_ok=True)
        if not file.is_file():
            file.touch()
        async with aiofiles.open(file, mode='ab') as f:
            async for chunk, _ in content.iter_chunks():
                await asyncio.sleep(0)
                await f.write(chunk)
                await update_progress(len(chunk))

    async def download_file(self, manager: Manager, domain: str, media_item: MediaItem, partial_file: Path,
                            headers: Dict, file_task: TaskID) -> None:
        """Starts a file"""
        async def save_content(content: aiohttp.StreamReader) -> None:
            await self._append_content(partial_file, content,
                                       partial(manager.progress_manager.file_progress.advance_file,
                                               file_task))

        await self._download(domain, manager, media_item, headers, save_content, partial_file, file_task)

