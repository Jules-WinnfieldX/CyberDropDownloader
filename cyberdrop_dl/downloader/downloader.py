from __future__ import annotations

import asyncio
import os
import traceback
from dataclasses import field, Field
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import filedate

from cyberdrop_dl.clients.download_client import is_4xx_client_error
from cyberdrop_dl.clients.errors import DownloadFailure, InvalidContentTypeFailure, DDOSGuardFailure
from cyberdrop_dl.utils.utilities import CustomHTTPStatus, log

if TYPE_CHECKING:
    from cyberdrop_dl.clients.download_client import DownloadClient
    from cyberdrop_dl.managers.manager import Manager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


def retry(f):
    """This function is a wrapper that handles retrying for failed downloads"""
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except DownloadFailure as e:
                media_item = args[0]
                await self.attempt_task_removal(media_item)

                if e.status != 999:
                    media_item.current_attempt += 1

                if not self.manager.config_manager.settings_data['Download_Options']['disable_download_attempt_limit']:
                    if media_item.current_attempt >= self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_attempts']:
                        if hasattr(e, "status"):
                            await self.manager.progress_manager.download_stats_progress.add_failure(e.status)
                            if hasattr(e, "message"):
                                await log(f"Download Failed: {media_item.url} with status {e.status} and message {e.message}", 40)
                                await self.manager.log_manager.write_download_error_log(media_item.url, f" {e.status} - {e.message}")
                            else:
                                await log(f"Download Failed: {media_item.url} with status {e.status}", 40)
                                await self.manager.log_manager.write_download_error_log(media_item.url, f" {e.status}")
                        else:
                            await self.manager.progress_manager.download_stats_progress.add_failure("Unknown")
                            await self.manager.log_manager.write_download_error_log(media_item.url, " See Log for Details")
                            await log(f"Download Failed: {media_item.url} with error {e}", 40)
                        await self.manager.progress_manager.download_progress.add_failed()
                        break

                if hasattr(e, "status"):
                    if hasattr(e, "message"):
                        await log(f"Download Failed: {media_item.url} with status {e.status} and message {e.message}", 40)
                    else:
                        await log(f"Download Failed: {media_item.url} with status {e.status}", 40)
                else:
                    await log(f"Download Failed: {media_item.url} with error {e}", 40)
                await log(f"Download Retrying: {media_item.url} with attempt {media_item.current_attempt}", 20)
            
            except DDOSGuardFailure as e:
                media_item = args[0]
                await self.attempt_task_removal(media_item)
                await log(f"Download Failed: {media_item.url} with error {e}", 40)
                await self.manager.log_manager.write_download_error_log(media_item.url, " DDOSGuard")
                await log(traceback.format_exc(), 40)
                await self.manager.progress_manager.download_stats_progress.add_failure("DDOSGuard")
                await self.manager.progress_manager.download_progress.add_failed()
                break
            
            except InvalidContentTypeFailure as e:
                media_item = args[0]
                await self.attempt_task_removal(media_item)
                await log(f"Download Failed: {media_item.url} received Invalid Content", 40)
                await self.manager.log_manager.write_download_error_log(media_item.url, "Invalid Content Received")
                await log(e.message, 40)
                await self.manager.progress_manager.download_stats_progress.add_failure("Invalid Content Type")
                await self.manager.progress_manager.download_progress.add_failed()
                break
            
            except Exception as e:
                media_item = args[0]
                await log(f"Download Failed: {media_item.url} with error {e}", 40)
                await self.attempt_task_removal(media_item)
                await log(traceback.format_exc(), 40)
                await self.manager.log_manager.write_download_error_log(media_item.url, " See Log For Details")
                await self.manager.progress_manager.download_stats_progress.add_failure("Unknown")
                await self.manager.progress_manager.download_progress.add_failed()
                break
    return wrapper


class Downloader:
    def __init__(self, manager: Manager, domain: str):
        self.manager: Manager = manager
        self.domain: str = domain

        self.client: DownloadClient = field(init=False)

        self._file_lock = manager.download_manager.file_lock
        self._semaphore: asyncio.Semaphore = field(init=False)

        self._additional_headers = {}

        self.processed_items: list = []
        self.waiting_items = 0
        self._current_attempt_filesize = {}

    async def startup(self) -> None:
        """Starts the downloader"""
        self.client = self.manager.client_manager.downloader_session
        self._semaphore = asyncio.Semaphore(await self.manager.download_manager.get_download_limit(self.domain))

        self.manager.path_manager.download_dir.mkdir(parents=True, exist_ok=True)
        if self.manager.config_manager.settings_data['Sorting']['sort_downloads']:
            self.manager.path_manager.sorted_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, media_item: MediaItem) -> None:
        """Runs the download loop"""
        self.waiting_items += 1
        media_item.current_attempt = 0

        await self._semaphore.acquire()
        self.waiting_items -= 1
        if media_item.url.path not in self.processed_items:
            self.processed_items.append(media_item.url.path)
            await self.manager.progress_manager.download_progress.update_total()

            await log(f"Download Starting: {media_item.url}", 20)
            async with self.manager.client_manager.download_session_limit:
                try:
                    if isinstance(media_item.file_lock_reference_name, Field):
                        media_item.file_lock_reference_name = media_item.filename
                    await self._file_lock.check_lock(media_item.file_lock_reference_name)
                    
                    await self.download(media_item)
                except Exception as e:
                    await log(f"Download Failed: {media_item.url} with error {e}", 40)
                    await log(traceback.format_exc(), 40)
                    await self.manager.progress_manager.download_stats_progress.add_failure("Unknown")
                    await self.manager.progress_manager.download_progress.add_failed()
                else:
                    await log(f"Download Finished: {media_item.url}", 20)
                finally:
                    await self._file_lock.release_lock(media_item.file_lock_reference_name)
        self._semaphore.release()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_file_can_download(self, media_item: MediaItem) -> bool:
        """Checks if the file can be downloaded"""
        if not await self.manager.download_manager.check_free_space():
            await log(f"Download Skip {media_item.url} due to insufficient free space", 10)
            return False
        if not await self.manager.download_manager.check_allowed_filetype(media_item):
            await log(f"Download Skip {media_item.url} due to filetype restrictions", 10)
            return False
        return True

    async def set_file_datetime(self, media_item: MediaItem, complete_file: Path) -> None:
        """Sets the file's datetime"""
        if self.manager.config_manager.settings_data['Download_Options']['disable_file_timestamps']:
            return
        if not isinstance(media_item.datetime, Field):
            file = filedate.File(str(complete_file))
            file.set(
                created=media_item.datetime,
                modified=media_item.datetime,
                accessed=media_item.datetime,
            )
            
    async def attempt_task_removal(self, media_item: MediaItem) -> None:
        """Attempts to remove the task from the progress bar"""
        if not isinstance(media_item.task_id, Field):
            try:
                await self.manager.progress_manager.file_progress.remove_file(media_item.task_id)
            except ValueError:
                pass
        media_item.task_id = field(init=False)
            
    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @retry
    async def download(self, media_item: MediaItem) -> None:
        """Downloads the media item"""
        if not await self.check_file_can_download(media_item):
            await self.manager.progress_manager.download_progress.add_skipped()
            return

        try:
            if not isinstance(media_item.current_attempt, int):
                media_item.current_attempt = 1

            if not await self.check_file_can_download(media_item):
                await self.manager.progress_manager.download_progress.add_skipped()
                return

            downloaded = await self.client.download_file(self.manager, self.domain, media_item)
            
            if downloaded:
                os.chmod(media_item.complete_file, 0o666)
                await self.set_file_datetime(media_item, media_item.complete_file)
                await self.attempt_task_removal(media_item)
                await self.manager.progress_manager.download_progress.add_completed()

        except (aiohttp.ClientPayloadError, aiohttp.ClientOSError, aiohttp.ClientResponseError, ConnectionResetError,
                DownloadFailure, FileNotFoundError, PermissionError, aiohttp.ServerDisconnectedError, 
                asyncio.TimeoutError, aiohttp.ServerTimeoutError) as e:
            if hasattr(e, "status"):
                if ((await is_4xx_client_error(e.status) and e.status != HTTPStatus.TOO_MANY_REQUESTS)
                        or e.status == HTTPStatus.SERVICE_UNAVAILABLE
                        or e.status == HTTPStatus.BAD_GATEWAY
                        or e.status == CustomHTTPStatus.WEB_SERVER_IS_DOWN):
                    await self.manager.progress_manager.download_progress.add_failed()
                    await self.manager.progress_manager.download_stats_progress.add_failure(e.status)
                    await self.attempt_task_removal(media_item)
                    if hasattr(e, "message"):
                        if not e.message:
                            e.message = "Download Failed"
                        await log(f"Download failed: {media_item.url} with status {e.status} and message {e.message}", 40)
                        await self.manager.log_manager.write_download_error_log(media_item.url, f" {e.status} - {e.message}")
                    else:
                        await log(f"Download Failed: {media_item.url} with status {e.status}", 40)
                        await self.manager.log_manager.write_download_error_log(media_item.url, f" {e.status}")
                    return

            if isinstance(media_item.partial_file, Path) and media_item.partial_file.is_file():
                size = media_item.partial_file.stat().st_size
                if media_item.filename in self._current_attempt_filesize and self._current_attempt_filesize[media_item.filename] >= size:
                    raise DownloadFailure(status=getattr(e, "status", type(e).__name__), message="Download failed")
                self._current_attempt_filesize[media_item.filename] = size
                media_item.current_attempt = 0
                raise DownloadFailure(status=999, message="Download timeout reached, retrying")

            raise DownloadFailure(status=getattr(e, "status", type(e).__name__), message=repr(e))
