from __future__ import annotations

import asyncio
import contextlib
import itertools
import logging
from http import HTTPStatus
from pathlib import Path
from random import gauss
from typing import TYPE_CHECKING, Dict, Any, Tuple, Optional

import aiofiles
import aiohttp.client_exceptions
from rich.live import Live

from cyberdrop_dl.base_functions.base_functions import (
    adjust,
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
    album_progress,
    cascade_progress,
    domain_progress,
    file_progress,
    forum_progress,
    get_cascade_table,
    get_forum_table,
    overall_file_progress,
)

if TYPE_CHECKING:
    from rich.progress import TaskID


class Files:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self, total_files: int):
        self.completed_files_task_id = overall_file_progress.add_task("[green]Completed", total=total_files)
        self.completed_files = 0
        self.skipped_files_task_id = overall_file_progress.add_task("[yellow]Skipped", total=total_files)
        self.skipped_files = 0
        self.failed_files_task_id = overall_file_progress.add_task("[red]Failed", total=total_files)
        self.failed_files = 0

    async def add_completed(self):
        overall_file_progress.advance(self.completed_files_task_id, 1)
        self.completed_files += 1

    async def add_skipped(self):
        overall_file_progress.advance(self.skipped_files_task_id, 1)
        self.skipped_files += 1

    async def add_failed(self):
        overall_file_progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def hide(self):
        overall_file_progress.update(self.completed_files_task_id, visible=False)
        overall_file_progress.update(self.skipped_files_task_id, visible=False)
        overall_file_progress.update(self.failed_files_task_id, visible=False)


class Downloader:
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
        self.delay = {'cyberfile': 1.0, 'anonfiles': 1.0, "coomer": 0.2, "kemono": 0.2}

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

    async def start_domain(self, cascade_task: TaskID) -> None:
        """Handler for domains and the progress bars for it"""
        domain_task = domain_progress.add_task("[light_pink3]" + self.domain.upper(), total=len(self.domain_obj.albums))
        for album, album_obj in self.domain_obj.albums.items():
            await self.start_album(domain_task, album, album_obj)
        cascade_progress.advance(cascade_task, 1)
        domain_progress.update(domain_task, visible=False)
        await self.download_session.exit_handler()

    async def start_album(self, domain_task: TaskID, album: str, album_obj: AlbumItem) -> None:
        """Handler for albums and the progress bars for it"""
        if await album_obj.is_empty():
            return
        task_description = album.split('/')[-1]
        task_description = task_description.encode("ascii", "ignore").decode().strip()
        task_description = await adjust(task_description)
        album_task = album_progress.add_task("[pink3]" + task_description.upper(), total=len(album_obj.media))
        download_tasks = []
        for media in album_obj.media:
            download_tasks.append(self.start_file(album_task, album, media))
        await asyncio.gather(*download_tasks)
        album_progress.update(album_task, visible=False)
        domain_progress.advance(domain_task, 1)

    async def start_file(self, album_task: TaskID, album: str, media: MediaItem) -> None:
        """Handler for files and the progress bars for it"""
        if media.complete or await self.SQL_Helper.check_complete_singular(self.domain, media.url):
            log(f"Previously Downloaded: {media.filename}", quiet=True)
            await self.files.add_skipped()
            album_progress.advance(album_task, 1)
            return
        async with self._semaphore:
            url_path = await get_db_path(media.url, self.domain)
            await self.download_file(album, media, url_path, album_task)

    @retry
    async def download_file(self, album: str, media: MediaItem, url_path: str, album_task: TaskID) -> None:
        """File downloader"""
        if not await check_free_space(self.required_free_space, self.download_dir):
            log("We've run out of free space.", quiet=True)
            await self.files.add_skipped()
            album_progress.advance(album_task, 1)
            return

        if not await allowed_filetype(media, self.exclude_images, self.exclude_videos, self.exclude_audio,
                                      self.exclude_other):
            log(f"Blocked by file extension: {media.filename}", quiet=True)
            await self.files.add_skipped()
            album_progress.advance(album_task, 1)
            return

        if self.block_sub_folders:
            album = album.split('/')[0]

        original_filename = media.original_filename
        filename = media.filename

        try:
            while await self.File_Lock.check_lock(filename):
                await asyncio.sleep(gauss(1, 1.5))
            await self.File_Lock.add_lock(filename)

            if url_path not in self.current_attempt:
                self.current_attempt[url_path] = 0

            current_throttle = self.client.throttle

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

            task_description = media.filename.encode("ascii", "ignore").decode().strip()
            task_description = await adjust(task_description)
            file_task = file_progress.add_task("[plum3]" + task_description, progress_type="file")

            if not await self.SQL_Helper.sql_check_old_existing(url_path) and not fake_download:
                await self.download_session.download_file(media, partial_file, current_throttle, resume_point,
                                                          self.proxy, headers, file_task)
                partial_file.rename(complete_file)

            await self.SQL_Helper.mark_complete(url_path, original_filename)
            if media.url.parts[-1] in self.current_attempt:
                self.current_attempt.pop(media.url.parts[-1])

            if fake_download:
                log(f"Already Downloaded: {media.filename} from {media.referer}", quiet=True)
                await self.files.add_skipped()
            else:
                await self.files.add_completed()
            album_progress.advance(album_task, 1)
            file_progress.update(file_task, visible=False)

            log(f"Completed Download: {media.filename} from {media.referer}", quiet=True)
            await self.File_Lock.remove_lock(filename)
            return

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ServerTimeoutError,
                DownloadFailure, FileNotFoundError, PermissionError) as e:
            if await self.File_Lock.check_lock(filename):
                await self.File_Lock.remove_lock(filename)

            with contextlib.suppress(Exception):
                file_progress.update(file_task, visible=False)

            if hasattr(e, "message"):
                logging.debug(f"\n{media.url} ({e.message})")

            if hasattr(e, "code"):
                if await is_4xx_client_error(e.code) and e.code != HTTPStatus.TOO_MANY_REQUESTS:
                    logger.debug("We ran into a 400 level error: %s", e.code)
                    log(f"Failed Download: {media.filename}", quiet=True)
                    await self.files.add_failed()
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.output_failed(media, e)
                    return
                if e.code == HTTPStatus.SERVICE_UNAVAILABLE or e.code == HTTPStatus.BAD_GATEWAY \
                        or e.code == CustomHTTPStatus.WEB_SERVER_IS_DOWN:
                    if hasattr(e, "message"):
                        if not e.message:
                            e.message = "Web server is down"
                        logging.debug(f"\n{media.url} ({e.message})")
                    log(f"Failed Download: {media.filename}", quiet=True)
                    await self.files.add_failed()
                    if url_path in self.current_attempt:
                        self.current_attempt.pop(url_path)
                    await self.output_failed(media, e)
                    return

                logger.debug("Error status code: %s", e.code)

            raise DownloadFailure(code=getattr(e, "code", 1), message=repr(e))

    async def output_failed(self, media: MediaItem, e: Any) -> None:
        if self.errored_output:
            async with aiofiles.open(self.errored_file, mode='a') as file:
                await file.write(f"{media.url},{media.referer},{e.message}\n")

    async def check_file_exists(self, complete_file: Path, partial_file: Path, media: MediaItem, album: str,
                                url_path: str, original_filename: str, current_throttle: float):
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
            complete_file = (self.download_dir / album / media.filename)
            partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

        return complete_file, partial_file, proceed

    async def iterate_filename(self, complete_file: Path, media: MediaItem, album: str) -> Tuple[Path, Path]:
        for iterations in itertools.count(1):
            filename = f"{complete_file.stem} ({iterations}){media.ext}"
            temp_complete_file = (self.download_dir / album / filename)
            if not temp_complete_file.exists() and not await self.SQL_Helper.check_filename(filename):
                media.filename = filename
                complete_file = (self.download_dir / album / media.filename)
                partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                break
        return complete_file, partial_file


async def download_cascade(args: Dict, Cascade: CascadeItem, SQL_Helper: SQLHelper, client: Client) -> None:
    """Handler for cascades and the progress bars for it"""
    progress_table = await get_cascade_table(args["Progress_Options"])
    total_files = await Cascade.get_total()
    files = Files(total_files)
    with Live(progress_table, refresh_per_second=args["Progress_Options"]["refresh_rate"]):
        cascade_task = cascade_progress.add_task("[light_salmon3]Domains", progress_type="cascade",
                                                 total=len(Cascade.domains))

        tasks = []
        for domain, domain_obj in Cascade.domains.items():
            downloader = Downloader(args, client, SQL_Helper, domain, domain_obj, files)
            tasks.append(downloader.start_domain(cascade_task))
        await asyncio.gather(*tasks)

        cascade_progress.update(cascade_task, visible=False)

    await files.hide()

    await clear()
    log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: "
              f"{files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")


async def download_forums(args: Dict, Forums: ForumItem, SQL_Helper: SQLHelper, client: Client) -> None:
    """Handler for forum threads and the progress bars for it"""
    progress_table = await get_forum_table(args["Progress_Options"])
    total_files = await Forums.get_total()
    files = Files(total_files)
    with Live(progress_table, refresh_per_second=args["Progress_Options"]["refresh_rate"]):
        forum_task = forum_progress.add_task("[orange3]FORUM THREADS", total=len(Forums.threads))
        for title, Cascade in Forums.threads.items():
            cascade_task = cascade_progress.add_task("[light_salmon3]" + title.upper(), total=len(Cascade.domains))

            tasks = []
            for domain, domain_obj in Cascade.domains.items():
                downloader = Downloader(args, client, SQL_Helper, domain, domain_obj, files)
                tasks.append(downloader.start_domain(cascade_task))
            await asyncio.gather(*tasks)

            cascade_progress.update(cascade_task, visible=False)
            forum_progress.advance(forum_task, 1)

    await clear()
    log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: "
              f"{files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")
