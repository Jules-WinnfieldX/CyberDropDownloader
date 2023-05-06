from __future__ import annotations

import asyncio
import itertools
import logging
from http import HTTPStatus
from pathlib import Path
from random import gauss
from typing import Dict, Any

import aiofiles
import aiohttp.client_exceptions
from tqdm import tqdm

from cyberdrop_dl.base_functions.base_functions import (
    clear,
    log,
    logger,
)
from cyberdrop_dl.base_functions.data_classes import AlbumItem, DomainItem, FileLock, ForumItem, MediaItem
from cyberdrop_dl.base_functions.error_classes import DownloadFailure
from cyberdrop_dl.base_functions.sql_helper import SQLHelper, get_db_path
from cyberdrop_dl.client.client import Client, DownloadSession

from .downloader_utils import (
    CustomHTTPStatus,
    allowed_filetype,
    basic_auth,
    check_free_space,
    get_threads_number,
    is_4xx_client_error,
    retry,
)


class Files:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self, progress: tqdm):
        self.progress = progress
        self.completed_files = 0
        self.skipped_files = 0
        self.failed_files = 0

    def add_completed(self) -> None:
        self.completed_files += 1
        self.progress.update(1)

    def add_skipped(self) -> None:
        self.skipped_files += 1
        self.progress.update(1)

    def add_failed(self) -> None:
        self.failed_files += 1
        self.progress.update(1)


class Old_Downloader:
    """Downloader class, directs downloading for domain objects"""

    def __init__(self, args: Dict, client: Client, SQL_Helper: SQLHelper,
                 domain: str, domain_obj: DomainItem, files: Files):
        self.client = client
        self.download_session = DownloadSession(client)
        self.File_Lock = FileLock()
        self.SQL_Helper = SQL_Helper

        self.domain = domain
        self.domain_obj = domain_obj

        self.errored_output = args['Runtime']['output_errored_urls']
        self.errored_file = args['Files']['errored_urls_file']

        self.files = files

        self.current_attempt: Dict[str, int] = {}
        max_workers = get_threads_number(args, domain)
        self._semaphore = asyncio.Semaphore(max_workers)
        self.delay = {'cyberfile': 1, 'anonfiles': 1, "coomer": 0.2, "kemono": 0.2}

        self.pixeldrain_api_key = args["Authentication"]["pixeldrain_api_key"]

        self.exclude_audio = args["Ignore"]["exclude_audio"]
        self.exclude_images = args["Ignore"]["exclude_images"]
        self.exclude_videos = args["Ignore"]["exclude_videos"]
        self.exclude_other = args["Ignore"]["exclude_other"]

        self.block_sub_folders = args['Runtime']['block_sub_folders']
        self.allowed_attempts = args["Runtime"]["attempts"]
        self.disable_attempt_limit = args["Runtime"]["disable_attempt_limit"]
        self.download_dir = args["Files"]["output_folder"]
        self.mark_downloaded = args["Runtime"]["skip_download_mark_completed"]
        self.proxy = args["Runtime"]["proxy"]
        self.required_free_space = args["Runtime"]["required_free_space"]

    async def start_domain(self) -> None:
        """Handler for domains and the progress bars for it"""
        for album, album_obj in self.domain_obj.albums.items():
            await self.start_album(album, album_obj)
        await self.download_session.exit_handler()

    async def start_album(self, album: str, album_obj: AlbumItem) -> None:
        """Handler for albums and the progress bars for it"""
        if await album_obj.is_empty():
            return
        download_tasks = []
        for media in album_obj.media:
            download_tasks.append(self.start_file(album, media))
        await asyncio.gather(*download_tasks)

    async def start_file(self, album: str, media: MediaItem) -> None:
        """Handler for files and the progress bars for it"""
        if media.complete or await self.SQL_Helper.check_complete_singular(self.domain, media.url):
            log(f"Previously Downloaded: {media.filename}", quiet=True)
            self.files.add_skipped()
            return
        async with self._semaphore:
            url_path = await get_db_path(media.url, self.domain)
            await self.download_file(album, media, url_path)

    @retry
    async def download_file(self, album: str, media: MediaItem, url_path: str) -> None:
        """File downloader"""
        if not await check_free_space(self.required_free_space, self.download_dir):
            log("We've run out of free space.", quiet=True)
            self.files.add_skipped()
            return

        if not await allowed_filetype(media, self.exclude_images, self.exclude_videos, self.exclude_audio,
                                      self.exclude_other):
            log(f"Blocked by file extension: {media.filename}", quiet=True)
            self.files.add_skipped()
            return

        if self.block_sub_folders:
            album = album.split('/')[0]

        try:
            while await self.File_Lock.check_lock(media.filename):
                await asyncio.sleep(gauss(1, 1.5))
            await self.File_Lock.add_lock(media.filename)

            if url_path not in self.current_attempt:
                self.current_attempt[url_path] = 0

            current_throttle = self.client.throttle

            original_filename = media.filename
            complete_file = (self.download_dir / album / media.filename)
            partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

            fake_download = False
            if self.mark_downloaded:
                fake_download = True

            complete_file, partial_file, proceed = await self.check_file_exists(complete_file, partial_file, media,
                                                                                album, url_path, original_filename,
                                                                                current_throttle)
            if not proceed:
                fake_download = True

            await self.SQL_Helper.update_pre_download(complete_file, media.filename, url_path, original_filename)

            resume_point = 0
            await self.SQL_Helper.sql_insert_temp(str(partial_file))
            range_num = None
            if partial_file.exists():
                resume_point = partial_file.stat().st_size
                range_num = f'bytes={resume_point}-'

            assert media.url.host is not None
            for key, value in self.delay.items():
                if key in media.url.host:
                    current_throttle = value

            headers = {"Authorization": await basic_auth("Cyberdrop-DL", self.pixeldrain_api_key)} \
                if (self.pixeldrain_api_key and "pixeldrain" in media.url.host) else {}
            if range_num:
                headers['Range'] = range_num

            if not await self.SQL_Helper.sql_check_old_existing(url_path) and not fake_download:
                await self.download_session.old_download_file(media, partial_file, current_throttle, resume_point,
                                                              self.proxy, headers)
                partial_file.rename(complete_file)

            await self.SQL_Helper.mark_complete(url_path, original_filename)
            if media.url.parts[-1] in self.current_attempt:
                self.current_attempt.pop(media.url.parts[-1])

            if fake_download:
                self.files.add_skipped()
            else:
                self.files.add_completed()

            log(f"Completed Download: {media.filename} from {media.referer}", quiet=True)
            await self.File_Lock.remove_lock(original_filename)
            return

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ServerTimeoutError,
                DownloadFailure, PermissionError) as e:
            if await self.File_Lock.check_lock(original_filename):
                await self.File_Lock.remove_lock(original_filename)

            if hasattr(e, "message"):
                logging.debug(f"\n{media.url} ({e.message})")

            if hasattr(e, "code"):
                if await is_4xx_client_error(e.code) and e.code != HTTPStatus.TOO_MANY_REQUESTS:
                    logger.debug("We ran into a 400 level error: %s", e.code)
                    log(f"Failed Download: {media.filename}", quiet=True)
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.handle_failed(media, e)
                    return
                if e.code == HTTPStatus.SERVICE_UNAVAILABLE or e.code == CustomHTTPStatus.WEB_SERVER_IS_DOWN:
                    if hasattr(e, "message"):
                        if not e.message:
                            e.message = "Web server is down"
                        logging.debug(f"\n{media.url} ({e.message})")
                    log(f"Failed Download: {media.filename}", quiet=True)
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.handle_failed(media, e)
                    return
                logger.debug("Error status code: %s", e.code)

            raise DownloadFailure(code=getattr(e, "code", 1), message=repr(e))

    def can_retry(self, url_path: str) -> bool:
        return self.disable_attempt_limit or self.current_attempt[url_path] < self.allowed_attempts - 1

    async def handle_failed(self, media: MediaItem, e: Any) -> None:
        self.files.add_failed()
        if self.errored_output:
            async with aiofiles.open(self.errored_file, mode='a') as file:
                await file.write(f"{media.url},{media.referer},{e.message}\n")

    async def check_file_exists(self, complete_file: Path, partial_file: Path, media: MediaItem, album: str,
                                url_path: str, original_filename: str,
                                current_throttle: float) -> tuple[Path, Path, bool]:
        """Complicated checker for if a file already exists, and was already downloaded"""
        expected_size = None
        proceed = True
        while True:
            if not complete_file.exists() and not partial_file.exists():
                break

            if not expected_size:
                expected_size = await self.download_session.get_filesize(media.url, str(media.referer),
                                                                         current_throttle)
            if complete_file.exists() and complete_file.stat().st_size == expected_size:
                proceed = False
                break

            downloaded_filename = await self.SQL_Helper.get_downloaded_filename(url_path, original_filename)
            if not downloaded_filename:
                for iterations in itertools.count(1):
                    filename = f"{complete_file.stem} ({iterations}){media.ext}"
                    temp_complete_file = (self.download_dir / album / filename)
                    if not temp_complete_file.exists() and not await self.SQL_Helper.check_filename(filename):
                        media.filename = filename
                        complete_file = (self.download_dir / album / media.filename)
                        partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                        break
                break

            if media.filename == downloaded_filename:
                if complete_file.exists():
                    proceed = False
                elif partial_file.exists() and partial_file.stat().st_size == expected_size:
                    proceed = False
                    partial_file.rename(complete_file)
                break

            media.filename = downloaded_filename
            complete_file = (self.download_dir / album / media.filename)
            partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

        return complete_file, partial_file, proceed


async def old_download_forums(args: Dict, Forums: ForumItem, SQL_Helper: SQLHelper, client: Client) -> None:
    """Handler for forum threads and the progress bars for it"""
    total_files = await Forums.get_total()
    with tqdm(total=total_files, unit_scale=True, unit='Files', leave=True, initial=0,
              desc="Files Downloaded") as progress:
        files = Files(progress)
        for title, Cascade in Forums.threads.items():
            tasks = []
            for domain, domain_obj in Cascade.domains.items():
                downloader = Old_Downloader(args, client, SQL_Helper, domain, domain_obj, files)
                tasks.append(downloader.start_domain())
            await asyncio.gather(*tasks)

    await clear()
    log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: "
              f"{files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")
