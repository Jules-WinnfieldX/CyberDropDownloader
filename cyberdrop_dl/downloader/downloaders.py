from __future__ import annotations

import asyncio
import contextlib
import itertools
import logging
from http import HTTPStatus
from random import gauss
from typing import TYPE_CHECKING, Any, Dict, Tuple, Coroutine, List, Optional

import aiohttp.client_exceptions
from rich.live import Live

from cyberdrop_dl.base_functions.base_functions import (
    FILE_FORMATS,
    clear,
    log,
    logger,
)
from cyberdrop_dl.base_functions.data_classes import (
    AlbumItem,
    CascadeItem,
    DomainItem,
    FileLock,
    ForumItem,
    MediaItem,
)
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
from .progress_definitions import (
    OverallFileProgress,
    ProgressMaster,
)

if TYPE_CHECKING:
    from pathlib import Path
    from rich.progress import TaskID

    from cyberdrop_dl.base_functions.base_functions import ErrorFileWriter


def _limit_concurrency(coroutines: List[Coroutine], semaphore: Optional[asyncio.Semaphore]) -> List[Coroutine]:
    if not semaphore:
        return coroutines

    async def limit_concurrency(coroutine: Coroutine) -> Coroutine:
        async with semaphore:
            return await coroutine

    return [limit_concurrency(coroutine) for coroutine in coroutines]


class CDLHelper:
    def __init__(self, args: Dict, client: Client, files: OverallFileProgress, SQL_Helper: SQLHelper,
                 error_writer: ErrorFileWriter):
        self.args = args

        # CDL Objects
        self.client = client
        self.files = files
        self.SQL_Helper = SQL_Helper
        self.error_writer = error_writer
        self.File_Lock = FileLock()

        # Limits
        self.delay = {'cyberdrop': 1.0, 'cyberfile': 1.0, 'anonfiles': 1.0, "coomer": 0.2, "kemono": 0.2}

        # Exclude Args
        self.exclude_audio = args["Ignore"]["exclude_audio"]
        self.exclude_images = args["Ignore"]["exclude_images"]
        self.exclude_videos = args["Ignore"]["exclude_videos"]
        self.exclude_other = args["Ignore"]["exclude_other"]

        # Runtime Args
        self.block_sub_folders = args['Runtime']['block_sub_folders']
        self.allowed_attempts = args["Runtime"]["attempts"]
        self.disable_attempt_limit = args["Runtime"]["disable_attempt_limit"]
        self.download_dir = args["Files"]["output_folder"]
        self.mark_downloaded = args["Runtime"]["skip_download_mark_completed"]
        self.proxy = args["Runtime"]["proxy"]
        self.required_free_space = args["Runtime"]["required_free_space"]

        # Filesize limits
        self.filesize_minimum_images = args["Runtime"]["filesize_minimum_images"]
        self.filesize_minimum_other = args["Runtime"]["filesize_minimum_other"]
        self.filesize_minimum_videos = args["Runtime"]["filesize_minimum_videos"]
        self.filesize_maximum_images = args["Runtime"]["filesize_maximum_images"]
        self.filesize_maximum_other = args["Runtime"]["filesize_maximum_other"]
        self.filesize_maximum_videos = args["Runtime"]["filesize_maximum_videos"]

        # Concurrency Limits
        self.threads_limit = asyncio.Semaphore(args["Runtime"]["max_concurrent_threads"]) if args["Runtime"][
            "max_concurrent_threads"] else None
        self.domains_limit = asyncio.Semaphore(args["Runtime"]["max_concurrent_domains"]) if args["Runtime"][
            "max_concurrent_domains"] else None
        self.albums_limit = asyncio.Semaphore(args["Runtime"]["max_concurrent_albums"]) if args["Runtime"][
            "max_concurrent_albums"] else None

        # API Keys
        self.pixeldrain_api_key = args["Authentication"]["pixeldrain_api_key"]

    def get_throttle(self, domain: str) -> float:
        """Get the throttle for a domain"""
        return self.delay.get(domain, self.client.throttle)

    async def check_filesize_limits(self, media: MediaItem, content_size: int) -> bool:
        if media.ext in FILE_FORMATS['Images']:
            if self.filesize_minimum_images and self.filesize_maximum_images:
                if content_size < self.filesize_minimum_images or content_size > self.filesize_maximum_images:
                    return False
            if content_size < self.filesize_minimum_images:
                return False
            if self.filesize_maximum_images and content_size > self.filesize_maximum_images:
                return False
        elif media.ext in FILE_FORMATS['Videos']:
            if self.filesize_minimum_videos and self.filesize_maximum_videos:
                if content_size < self.filesize_minimum_videos or content_size > self.filesize_maximum_videos:
                    return False
            if content_size < self.filesize_minimum_videos:
                return False
            if self.filesize_maximum_videos and content_size > self.filesize_maximum_videos:
                return False
        else:
            if self.filesize_minimum_other and self.filesize_maximum_other:
                if content_size < self.filesize_minimum_other or content_size > self.filesize_maximum_other:
                    return False
            if content_size < self.filesize_minimum_other:
                return False
            if self.filesize_maximum_other and content_size > self.filesize_maximum_other:
                return False
        return True


class Downloader:
    """Downloader class, directs downloading for domain objects"""

    def __init__(self, domain: str, CDL_Helper: CDLHelper, Progress_Master: ProgressMaster):
        self.domain = domain
        self.throttle = CDL_Helper.get_throttle(domain)

        max_workers = get_threads_number(CDL_Helper.args, domain)
        self._semaphore = asyncio.Semaphore(max_workers)
        self.current_attempt: Dict[str, int] = {}
        self.current_attempt_filesize: Dict[str, int] = {}

        self.download_session = DownloadSession(CDL_Helper.client)

        self.CDL_Helper = CDL_Helper
        self.Progress_Master = Progress_Master

    async def download(self, album: str, media: MediaItem, url_path: str, album_task: TaskID) -> None:
        try:
            async with self._semaphore:
                await self.download_file(album, media, url_path, album_task)
        except RuntimeError as e:
            return

    @retry
    async def download_file(self, album: str, media: MediaItem, url_path: str, album_task: TaskID) -> None:
        """File downloader"""
        if not await check_free_space(self.CDL_Helper.required_free_space, self.CDL_Helper.download_dir):
            log("We've run out of free space.", quiet=True)
            await self.CDL_Helper.files.add_skipped()
            return

        if not await allowed_filetype(media, self.CDL_Helper.exclude_images, self.CDL_Helper.exclude_videos,
                                      self.CDL_Helper.exclude_audio, self.CDL_Helper.exclude_other):
            log(f"Blocked by file extension: {media.filename}", quiet=True)
            await self.CDL_Helper.files.add_skipped()
            return

        if self.CDL_Helper.block_sub_folders:
            album = album.split('/')[0]

        original_filename = media.original_filename
        filename = media.filename

        try:
            if self.CDL_Helper.mark_downloaded:
                complete_file = (self.CDL_Helper.download_dir / album / media.filename)
                log(f"Skip Download Flag Set: {media.filename} from {media.referer}", quiet=True)
                await self.CDL_Helper.SQL_Helper.update_pre_download(complete_file, media.filename, url_path, original_filename)
                await self.CDL_Helper.SQL_Helper.mark_complete(url_path, original_filename)
                await self.CDL_Helper.files.add_skipped()
                return

            while await self.CDL_Helper.File_Lock.check_lock(filename):
                await asyncio.sleep(gauss(1, 1.5))
            await self.CDL_Helper.File_Lock.add_lock(filename)

            if url_path not in self.current_attempt:
                self.current_attempt[url_path] = 0

            complete_file = (self.CDL_Helper.download_dir / album / media.filename)
            partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

            headers = {}
            if self.CDL_Helper.pixeldrain_api_key and "pixeldrain" in media.url.host:
                headers["Authorization"] = await basic_auth("Cyberdrop-DL", self.CDL_Helper.pixeldrain_api_key)

            complete_file, partial_file, proceed, expected_size = await self.check_file_exists(complete_file,
                                                                                               partial_file, media,
                                                                                               album, url_path,
                                                                                               original_filename,
                                                                                               self.throttle, headers)

            download_bool = proceed
            await self.CDL_Helper.SQL_Helper.update_pre_download(complete_file, media.filename, url_path, original_filename)

            filesize_check = await self.CDL_Helper.check_filesize_limits(media, expected_size)
            if not filesize_check:
                log(f"Filesize out of specified range: {media.url}", quiet=True)
                await self.CDL_Helper.files.add_skipped()
                await self.CDL_Helper.File_Lock.remove_lock(filename)
                return

            await self.CDL_Helper.SQL_Helper.sql_insert_temp(str(partial_file))
            resume_point = partial_file.stat().st_size if partial_file.exists() else 0

            assert media.url.host is not None

            headers['Range'] = f'bytes={resume_point}-'

            file_task = await self.Progress_Master.FileProgress.add_file(media.filename, expected_size)

            if not await self.CDL_Helper.SQL_Helper.sql_check_old_existing(url_path) and download_bool:
                await self.download_session.download_file(self.Progress_Master, media, partial_file, self.throttle,
                                                          resume_point, self.CDL_Helper.proxy, headers, file_task)
                partial_file.rename(complete_file)

            await self.CDL_Helper.SQL_Helper.mark_complete(url_path, original_filename)
            if media.url.parts[-1] in self.current_attempt:
                self.current_attempt.pop(media.url.parts[-1])

            if not download_bool:
                log(f"Already Downloaded: {media.filename} from {media.referer}", quiet=True)
                await self.CDL_Helper.files.add_skipped()
            else:
                await self.CDL_Helper.files.add_completed()
            await self.Progress_Master.FileProgress.mark_file_completed(file_task)

            log(f"Completed Download: {media.filename} from {media.referer}", quiet=True)
            await self.CDL_Helper.File_Lock.remove_lock(filename)
            return

        except (aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ServerTimeoutError) as e:
            if await self.CDL_Helper.File_Lock.check_lock(filename):
                await self.CDL_Helper.File_Lock.remove_lock(filename)

            with contextlib.suppress(Exception):
                await self.Progress_Master.FileProgress.remove_file(file_task)

            if partial_file.is_file():
                size = partial_file.stat().st_size
                if partial_file.name not in self.current_attempt_filesize:
                    self.current_attempt_filesize[filename] = size
                elif self.current_attempt_filesize[filename] > size:
                    self.current_attempt_filesize[filename] = size
                else:
                    raise DownloadFailure(status=getattr(e, "status", 1), message="Download timeout reached, retrying")
                raise DownloadFailure(status=999, message="Download timeout reached, retrying")

            raise DownloadFailure(status=getattr(e, "status", 1), message=repr(e))

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ClientResponseError, DownloadFailure, FileNotFoundError,
                PermissionError) as e:
            if await self.CDL_Helper.File_Lock.check_lock(filename):
                await self.CDL_Helper.File_Lock.remove_lock(filename)

            with contextlib.suppress(Exception):
                await self.Progress_Master.FileProgress.remove_file(file_task)

            if hasattr(e, "message"):
                logging.debug(f"\n{media.url} ({e.message})")

            if hasattr(e, "status"):
                if await is_4xx_client_error(e.status) and e.status != HTTPStatus.TOO_MANY_REQUESTS:
                    logger.debug("We ran into a 400 level error: %s", e.status)
                    log(f"Failed Download: {media.filename}", quiet=True)
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.handle_failed(media, e)
                    return

                if e.status == HTTPStatus.SERVICE_UNAVAILABLE or e.status == HTTPStatus.BAD_GATEWAY \
                        or e.status == CustomHTTPStatus.WEB_SERVER_IS_DOWN:
                    if hasattr(e, "message"):
                        if not e.message:
                            e.message = "Web server is down"
                        logging.debug(f"\n{media.url} ({e.message})")
                    log(f"Failed Download: {media.filename}", quiet=True)
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.handle_failed(media, e)
                    return

                logger.debug("Error status code: %s", e.status)

            raise DownloadFailure(status=getattr(e, "status", 1), message=repr(e))

    def can_retry(self, url_path: str) -> bool:
        return self.CDL_Helper.disable_attempt_limit or self.current_attempt[
            url_path] < self.CDL_Helper.allowed_attempts - 1

    async def handle_failed(self, media: MediaItem, e: Any) -> None:
        await self.CDL_Helper.files.add_failed()
        await self.CDL_Helper.error_writer.write_errored_download(media.url, media.referer, e.message)

    async def check_file_exists(self, complete_file: Path, partial_file: Path, media: MediaItem, album: str,
                                url_path: str, original_filename: str,
                                current_throttle: float, headers: Dict) -> tuple[Path, Path, bool, int]:
        """Complicated checker for if a file already exists, and was already downloaded"""
        expected_size = None
        proceed = True
        while True:
            if not expected_size:
                expected_size = await self.download_session.get_filesize(media.url, str(media.referer),
                                                                         current_throttle, headers)
            if not complete_file.exists() and not partial_file.exists():
                break

            if complete_file.exists() and complete_file.stat().st_size == expected_size:
                proceed = False
                break

            downloaded_filename = await self.CDL_Helper.SQL_Helper.get_downloaded_filename(url_path, original_filename)
            if not downloaded_filename:
                complete_file, partial_file = await self.iterate_filename(complete_file, media, album)
                break

            if media.filename == downloaded_filename:
                if partial_file.exists():
                    if partial_file.stat().st_size == expected_size:
                        proceed = False
                        partial_file.rename(complete_file)
                elif complete_file.exists():
                    if complete_file.stat().st_size == expected_size:
                        proceed = False
                    else:
                        complete_file, partial_file = await self.iterate_filename(complete_file, media, album)
                break

            media.filename = downloaded_filename
            complete_file = (self.CDL_Helper.download_dir / album / media.filename)
            partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

        return complete_file, partial_file, proceed, expected_size

    async def iterate_filename(self, complete_file: Path, media: MediaItem, album: str) -> Tuple[Path, Path]:
        for iterations in itertools.count(1):
            filename = f"{complete_file.stem} ({iterations}){media.ext}"
            temp_complete_file = (self.CDL_Helper.download_dir / album / filename)
            if not temp_complete_file.exists() and not await self.CDL_Helper.SQL_Helper.check_filename(filename):
                media.filename = filename
                complete_file = (self.CDL_Helper.download_dir / album / media.filename)
                partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                break
        return complete_file, partial_file


class DownloadManager:
    def __init__(self, CDL_Helper: CDLHelper, Progress_Master: ProgressMaster):
        self.downloaders: Dict[str, Downloader] = {}
        self.CDL_Helper = CDL_Helper
        self.Progress_Master = Progress_Master

    async def get_downloader(self, domain: str) -> Downloader:
        if domain not in self.downloaders:
            self.downloaders[domain] = Downloader(domain, self.CDL_Helper, self.Progress_Master)
        return self.downloaders[domain]


class DownloadDirector:
    def __init__(self, args: Dict, Forums: ForumItem, SQL_Helper: SQLHelper, client: Client,
                 error_writer: ErrorFileWriter):
        self.Progress_Master = ProgressMaster(args["Progress_Options"])
        self.CDL_Helper = CDLHelper(args, client, self.Progress_Master.OverallFileProgress, SQL_Helper, error_writer)
        self.Download_Manager = DownloadManager(self.CDL_Helper, self.Progress_Master)

        self.Forums = Forums

    async def start(self):
        await self.CDL_Helper.files.update_total(await self.Forums.get_total())

        progress_table = await self.Progress_Master.get_table()
        with Live(progress_table, refresh_per_second=self.Progress_Master.refresh_rate):
            forum_task = await self.Progress_Master.ForumProgress.add_forum(len(self.Forums.threads))
            cascade_tasks = []
            for title, Cascade in self.Forums.threads.items():
                cascade_tasks.append(self.start_cascade(forum_task, title, Cascade))
            await asyncio.gather(*_limit_concurrency(cascade_tasks, self.CDL_Helper.threads_limit))

        await clear()
        completed_files, skipped_files, failed_files = await self.Progress_Master.OverallFileProgress.return_totals()
        log(f"| [green]Files Complete: {completed_files}[/green] - [yellow]Files Skipped:  {skipped_files}[/yellow] - [red]Files Failed: {failed_files}[/red] |")

        for downloader in self.Download_Manager.downloaders.values():
            await downloader.download_session.exit_handler()

    async def start_cascade(self, forum_task: TaskID, title: str, Cascade: CascadeItem) -> None:
        cascade_task = await self.Progress_Master.CascadeProgress.add_cascade(title, len(Cascade.domains))
        domain_tasks = []
        for domain, domain_obj in Cascade.domains.items():
            domain_tasks.append(self.start_domain(cascade_task, title, domain, domain_obj))
        await asyncio.gather(*_limit_concurrency(domain_tasks, self.CDL_Helper.domains_limit))
        await self.Progress_Master.CascadeProgress.mark_cascade_completed(cascade_task)
        await self.Progress_Master.ForumProgress.advance_forum(forum_task)

    async def start_domain(self, cascade_task: TaskID, title: str, domain: str, domain_obj: DomainItem) -> None:
        """Handler for domains and the progress bars for it"""
        downloader = await self.Download_Manager.get_downloader(domain)

        domain_task = await self.Progress_Master.DomainProgress.add_domain(domain, len(domain_obj.albums))
        album_tasks = []
        for album, album_obj in domain_obj.albums.items():
            album_tasks.append(self.start_album(downloader, domain_task, domain, album, album_obj))
        await asyncio.gather(*_limit_concurrency(album_tasks, self.CDL_Helper.albums_limit))
        await self.Progress_Master.CascadeProgress.advance_cascade(cascade_task)
        await self.Progress_Master.DomainProgress.mark_domain_completed(domain, domain_task)

    async def start_album(self, downloader: Downloader, domain_task: TaskID, domain: str, album: str,
                          album_obj: AlbumItem) -> None:
        """Handler for albums and the progress bars for it"""
        if await album_obj.is_empty():
            return

        album_task = await self.Progress_Master.AlbumProgress.add_album(album, len(album_obj.media))
        download_tasks = []
        for media in album_obj.media:
            download_tasks.append(self.start_file(downloader, album_task, domain, album, media))
        await asyncio.gather(*download_tasks)
        await self.Progress_Master.DomainProgress.advance_domain(domain_task)
        await self.Progress_Master.AlbumProgress.mark_album_completed(album, album_task)

    async def start_file(self, downloader: Downloader, album_task: TaskID, domain: str, album: str,
                         media: MediaItem) -> None:
        """Handler for files and the progress bars for it"""
        if media.complete or await self.CDL_Helper.SQL_Helper.check_complete_singular(domain, media.url):
            log(f"Previously Downloaded: {media.filename}", quiet=True)
            await self.CDL_Helper.files.add_skipped()
            await self.Progress_Master.AlbumProgress.advance_album(album_task)
            return

        url_path = await get_db_path(media.url, domain)
        await downloader.download(album, media, url_path, album_task)
        await self.Progress_Master.AlbumProgress.advance_album(album_task)
