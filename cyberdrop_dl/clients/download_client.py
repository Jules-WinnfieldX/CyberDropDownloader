from __future__ import annotations

import asyncio
import copy
import itertools
import os
from http import HTTPStatus
from functools import wraps, partial
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import aiofiles
import aiohttp
from aiohttp import ClientSession

from cyberdrop_dl.clients.errors import DownloadFailure, InvalidContentTypeFailure
from cyberdrop_dl.utils.utilities import FILE_FORMATS, log

if TYPE_CHECKING:
    from typing import Callable, Coroutine, Any

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
                                         cookie_jar=self.client_manager.cookies, timeout=self._timeouts,
                                         trace_configs=self.trace_configs) as client:
            kwargs['client_session'] = client
            return await func(self, *args, **kwargs)
    return wrapper


class DownloadClient:
    """AIOHTTP operations for downloading"""
    def __init__(self, manager: Manager, client_manager: ClientManager):
        self.manager = manager
        self.client_manager = client_manager
        
        self._headers = {"user-agent": client_manager.user_agent}
        self._timeouts = aiohttp.ClientTimeout(total=client_manager.read_timeout + client_manager.connection_timeout,
                                               connect=client_manager.connection_timeout)
        self._global_limiter = self.client_manager.global_rate_limiter

        self.trace_configs = []
        if os.getenv("PYCHARM_HOSTED") is not None:
            async def on_request_start(session, trace_config_ctx, params):
                await log(f"Starting download {params.method} request to {params.url}", 40)

            async def on_request_end(session, trace_config_ctx, params):
                await log(f"Finishing download {params.method} request to {params.url}", 40)
                await log(f"Response status for {params.url}: {params.response.status}", 40)

            trace_config = aiohttp.TraceConfig()
            trace_config.on_request_start.append(on_request_start)
            trace_config.on_request_end.append(on_request_end)
            self.trace_configs.append(trace_config)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @limiter
    async def _download(self, domain: str, manager: Manager, media_item: MediaItem,
                        save_content: Callable[[aiohttp.StreamReader], Coroutine[Any, Any, None]], client_session: ClientSession) -> bool:
        """Downloads a file"""
        headers = copy.deepcopy(self._headers)
        headers['Referer'] = str(media_item.referer)
        if domain == "pixeldrain":
            if self.manager.config_manager.authentication_data['PixelDrain']['pixeldrain_api_key']:
                headers["Authorization"] = await self.manager.download_manager.basic_auth("Cyberdrop-DL", self.manager.config_manager.authentication_data['PixelDrain']['pixeldrain_api_key'])

        downloaded_filename = await self.manager.db_manager.history_table.get_downloaded_filename(domain, media_item)
        download_dir = await self.get_download_dir(media_item)
        media_item.partial_file = download_dir / f"{downloaded_filename}.part"
        
        resume_point = 0
        if isinstance(media_item.partial_file, Path) and media_item.partial_file.exists():
            resume_point = media_item.partial_file.stat().st_size if media_item.partial_file.exists() else 0
            headers['Range'] = f'bytes={resume_point}-'

        await asyncio.sleep(self.client_manager.download_delay)

        async with client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as resp:
            if resp.status == HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE:
                media_item.partial_file.unlink()
                
            await self.client_manager.check_http_status(resp, download=True)
            content_type = resp.headers.get('Content-Type')
            
            media_item.filesize = int(resp.headers.get('Content-Length', '0'))
            if not isinstance(media_item.complete_file, Path):
                proceed, skip = await self.get_final_file_info(media_item, domain)
                await self.mark_incomplete(media_item, domain)
                if skip:
                    await self.manager.progress_manager.download_progress.add_skipped()
                    return False
                if not proceed:
                    await log(f"Skipping {media_item.url} as it has already been downloaded", 10)
                    await self.manager.progress_manager.download_progress.add_previously_completed(False)
                    await self.mark_completed(media_item, domain)
                    return False
            
            ext = Path(media_item.filename).suffix.lower()
            if content_type and any(s in content_type.lower() for s in ('html', 'text')) and ext not in FILE_FORMATS['Text']:
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting other")

            if resp.status != HTTPStatus.PARTIAL_CONTENT and media_item.partial_file.is_file():
                media_item.partial_file.unlink()
                
            media_item.task_id = await self.manager.progress_manager.file_progress.add_task(f"({domain.upper()}) {media_item.filename}", media_item.filesize + resume_point)
            if media_item.partial_file.is_file():
                resume_point = media_item.partial_file.stat().st_size
                await self.manager.progress_manager.file_progress.advance_file(media_item.task_id, resume_point)

            await save_content(resp.content)
            return True

    async def _append_content(self, media_item, content: aiohttp.StreamReader, update_progress: partial) -> None:
        """Appends content to a file"""
        if not await self.client_manager.manager.download_manager.check_free_space():
            raise DownloadFailure(status="No Free Space", message="Not enough free space")

        media_item.partial_file.parent.mkdir(parents=True, exist_ok=True)
        if not media_item.partial_file.is_file():
            media_item.partial_file.touch()
        async with aiofiles.open(media_item.partial_file, mode='ab') as f:
            async for chunk, _ in content.iter_chunks():
                await asyncio.sleep(0)
                await f.write(chunk)
                await update_progress(len(chunk))
        if not content.total_bytes and not media_item.partial_file.stat().st_size:
            media_item.partial_file.unlink()
            raise DownloadFailure(status=HTTPStatus.INTERNAL_SERVER_ERROR, message="File is empty")

    async def download_file(self, manager: Manager, domain: str, media_item: MediaItem) -> bool:
        """Starts a file"""
        if self.manager.config_manager.settings_data['Download_Options']['skip_download_mark_completed']:
            await log(f"Download Skip {media_item.url} due to mark completed option", 10)
            await self.manager.progress_manager.download_progress.add_skipped()
            await self.mark_incomplete(media_item, domain)
            await self.mark_completed(media_item, domain)
            return False
        
        async def save_content(content: aiohttp.StreamReader) -> None:
            await self._append_content(media_item, content, partial(manager.progress_manager.file_progress.advance_file, media_item.task_id))

        downloaded = await self._download(domain, manager, media_item, save_content)
        if downloaded:
            media_item.partial_file.rename(media_item.complete_file)
            await self.mark_completed(media_item, domain)
        return downloaded
        
    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""
    
    async def mark_incomplete(self, media_item: MediaItem, domain: str) -> None:
        """Marks the media item as incomplete in the database"""
        await self.manager.db_manager.history_table.insert_incompleted(domain, media_item)

    async def mark_completed(self, media_item: MediaItem, domain: str) -> None:
        """Marks the media item as completed in the database"""
        await self.manager.db_manager.history_table.mark_complete(domain, media_item)
    
    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""
    
    async def get_download_dir(self, media_item: MediaItem) -> Path:
        """Returns the download directory for the media item"""
        download_folder = media_item.download_folder
        if self.manager.args_manager.retry:
            return download_folder

        if self.manager.config_manager.settings_data['Download_Options']['block_download_sub_folders']:
            while download_folder.parent != self.manager.path_manager.download_dir:
                download_folder = download_folder.parent
            media_item.download_folder = download_folder
        return download_folder
    
    async def get_final_file_info(self, media_item: MediaItem, domain: str) -> tuple[bool, bool]:
        """Complicated checker for if a file already exists, and was already downloaded"""
        download_dir = await self.get_download_dir(media_item)
        media_item.complete_file = download_dir / media_item.filename
        media_item.partial_file = media_item.complete_file.with_suffix(media_item.complete_file.suffix + '.part')
        
        expected_size = media_item.filesize if isinstance(media_item.filesize, int) else None
        proceed = True
        skip = False
        while True:
            if expected_size:
                file_size_check = await self.check_filesize_limits(media_item)
                if not file_size_check:
                    await log(f"Download Skip {media_item.url} due to filesize restrictions", 10)
                    proceed = False
                    skip = True
                    return proceed, skip

            if not media_item.complete_file.exists() and not media_item.partial_file.exists():
                break

            if media_item.complete_file.exists() and media_item.complete_file.stat().st_size == media_item.filesize:
                proceed = False
                break

            downloaded_filename = await self.manager.db_manager.history_table.get_downloaded_filename(domain, media_item)
            if not downloaded_filename:
                media_item.complete_file, media_item.partial_file = await self.iterate_filename(media_item.complete_file, media_item)
                break

            if media_item.filename == downloaded_filename:
                if media_item.partial_file.exists():
                    if media_item.partial_file.stat().st_size >= media_item.filesize != 0:
                        media_item.partial_file.unlink()
                    if media_item.partial_file.stat().st_size == media_item.filesize:
                        if media_item.complete_file.exists():
                            new_complete_filename, new_partial_file = await self.iterate_filename(media_item.complete_file, media_item)
                            media_item.partial_file.rename(new_complete_filename)
                            proceed = False

                            media_item.complete_file = new_complete_filename
                            media_item.partial_file = new_partial_file
                        else:
                            proceed = False
                            media_item.partial_file.rename(media_item.complete_file)
                elif media_item.complete_file.exists():
                    if media_item.complete_file.stat().st_size == media_item.filesize:
                        proceed = False
                    else:
                        media_item.complete_file, media_item.partial_file = await self.iterate_filename(media_item.complete_file, media_item)
                break

            media_item.filename = downloaded_filename
        media_item.download_filename = media_item.complete_file.name
        return proceed, skip

    async def iterate_filename(self, complete_file: Path, media_item: MediaItem) -> Tuple[Path, Path]:
        """Iterates the filename until it is unique"""
        partial_file = None
        for iteration in itertools.count(1):
            filename = f"{complete_file.stem} ({iteration}){media_item.ext}"
            temp_complete_file = media_item.download_folder / filename
            if not temp_complete_file.exists() and not await self.manager.db_manager.history_table.check_filename_exists(filename):
                media_item.filename = filename
                complete_file = media_item.download_folder / media_item.filename
                partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                break
        return complete_file, partial_file
    
    async def check_filesize_limits(self, media: MediaItem) -> bool:
        """Checks if the file size is within the limits"""
        max_video_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['maximum_video_size']
        min_video_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['minimum_video_size']
        max_image_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['maximum_image_size']
        min_image_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['minimum_image_size']
        max_other_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['maximum_other_size']
        min_other_filesize = self.manager.config_manager.settings_data['File_Size_Limits']['minimum_other_size']

        if media.ext in FILE_FORMATS['Images']:
            if max_image_filesize and min_image_filesize:
                if media.filesize < min_image_filesize or media.filesize > max_image_filesize:
                    return False
            if media.filesize < min_image_filesize:
                return False
            if max_image_filesize and media.filesize > max_image_filesize:
                return False
        elif media.ext in FILE_FORMATS['Videos']:
            if max_video_filesize and min_video_filesize:
                if media.filesize < min_video_filesize or media.filesize > max_video_filesize:
                    return False
            if media.filesize < min_video_filesize:
                return False
            if max_video_filesize and media.filesize > max_video_filesize:
                return False
        else:
            if max_other_filesize and min_other_filesize:
                if media.filesize < min_other_filesize or media.filesize > max_other_filesize:
                    return False
            if media.filesize < min_other_filesize:
                return False
            if max_other_filesize and media.filesize > max_other_filesize:
                return False
        return True
