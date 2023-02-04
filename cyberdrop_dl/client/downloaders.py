from __future__ import annotations

import asyncio
import logging
import multiprocessing
from base64 import b64encode
from functools import wraps
from random import gauss

import aiohttp.client_exceptions
from rich.progress import TaskID
from yarl import URL

from .progress_definitions import CascadeProgress, ForumsProgress
from ..base_functions.base_functions import log, logger, check_free_space, allowed_filetype, get_db_path
from ..base_functions.error_classes import DownloadFailure
from ..base_functions.sql_helper import SQLHelper
from ..base_functions.data_classes import AlbumItem, CascadeItem, FileLock, ForumItem, DomainItem, MediaItem
from ..client.client import Client, DownloadSession
from ..scraper.Scraper import ScrapeMapper


async def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


def retry(f):
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except DownloadFailure as e:
                if not self.disable_attempt_limit:
                    # TODO ALL THIS BELOW
                    if self.current_attempt[args[0].parts[-1]] >= self.attempts - 1:
                        logger.debug('Skipping %s...', args[0])
                        raise
                logger.debug(e)
                logger.debug(f'Retrying ({self.current_attempt[args[0].parts[-1]]}) {args[0]}...')
                self.current_attempt[args[0].parts[-1]] += 1

                await asyncio.sleep(2)
    return wrapper


class Files:
    def __init__(self):
        self.completed_files = 0
        self.skipped_files = 0
        self.failed_files = 0


class Downloader:
    def __init__(self, args: dict, client: Client, SQL_Helper: SQLHelper, scraper: ScrapeMapper, max_workers: int,
                 domain: str, domain_obj: DomainItem, semaphore: asyncio.Semaphore, files: Files):
        self.backup_scraper = scraper
        self.client = client
        self.download_session = DownloadSession(client, args["Ratelimiting"]["connection_timeout"])
        self.File_Lock = FileLock()
        self.SQL_Helper = SQL_Helper

        self.domain = domain
        self.domain_obj = domain_obj

        self.files = files

        self.current_attempt = {}
        self.max_workers = max_workers
        self._semaphore = semaphore
        self.delay = {'cyberfile.is': 1, 'anonfiles.com': 1}

        self.pixeldrain_api_key = args["Authentication"]["pixeldrain_api_key"]

        self.ignore_history = args["Ignore"]["ignore_history"]
        self.exclude_audio = args["Ignore"]["exclude_audio"]
        self.exclude_images = args["Ignore"]["exclude_images"]
        self.exclude_videos = args["Ignore"]["exclude_videos"]
        self.exclude_other = args["Ignore"]["exclude_other"]

        self.allowed_attempts = args["Runtime"]["attempts"]
        self.allow_insecure_connections = args["Runtime"]["allow_insecure_connections"]
        self.disable_attempt_limit = args["Runtime"]["disable_attempt_limit"]
        self.download_dir = args["Files"]["output_folder"]
        self.mark_downloaded = args["Runtime"]["mark_downloaded"]
        self.proxy = args["Runtime"]["proxy"]
        self.required_free_space = args["Runtime"]["required_free_space"]

    async def start_domain(self, progress: CascadeProgress, cascade_task: TaskID):
        domain_task = progress.add_task("[light_pink3]"+self.domain.upper(), progress_type="domain", total=len(self.domain_obj.albums))
        for album, album_obj in self.domain_obj.albums.items():
            await self.start_album(progress, domain_task, album, album_obj)
        progress.advance(cascade_task, 1)
        progress.update(domain_task, visible=False)
        progress.update(domain_task, total=len(self.domain_obj.albums), completed=len(self.domain_obj.albums))

    async def start_album(self, progress: CascadeProgress, domain_task: TaskID, album: str, album_obj: AlbumItem):
        album_task = progress.add_task("[pink3]"+album.upper().split("/")[-1], progress_type="album", total=len(album_obj.media))
        download_tasks = []
        for media in album_obj.media:
            download_tasks.append(self.start_file(progress, album_task, album, media))
        await asyncio.gather(*download_tasks)
        progress.update(album_task, visible=False)
        progress.advance(domain_task, 1)

    async def start_file(self, progress: CascadeProgress, album_task: TaskID, album: str, media: MediaItem):
        async with self._semaphore:
            await self.download_file(progress, album_task, album, media)

    @retry
    async def download_file(self, progress: CascadeProgress, album_task: TaskID, album: str, media: MediaItem):
        if media.complete:
            await log(f"Previously Downloaded: {media.filename}", quiet=True)
            self.files.skipped_files += 1
            progress.advance(album_task, 1)
            return

        if not await check_free_space(self.required_free_space, self.download_dir):
            await log("We've run out of free space.", quiet=True)
            self.files.skipped_files += 1
            progress.advance(album_task, 1)
            return

        if not await allowed_filetype(media, self.exclude_images, self.exclude_videos, self.exclude_audio, self.exclude_other):
            await log(f"Blocked by file extension: {media.filename}", quiet=True)
            self.files.skipped_files += 1
            progress.advance(album_task, 1)
            return

        while await self.File_Lock.check_lock(media.filename):
            await asyncio.sleep(gauss(1, 1.5))
        await self.File_Lock.add_lock(media.filename)

        if media.url.parts[-1] not in self.current_attempt:
            self.current_attempt[media.url.parts[-1]] = 0

        current_throttle = self.client.throttle
        url_path = await get_db_path(URL(media.url))

        original_filename = media.filename
        complete_file = (self.download_dir / album / media.filename)
        partial_file = complete_file.with_suffix(complete_file.suffix + '.part')

        while True:
            if complete_file.exists() or partial_file.exists():
                downloaded_filename = await self.SQL_Helper.get_downloaded_filename(url_path, original_filename)
                if downloaded_filename:
                    if media.filename == downloaded_filename:
                        if complete_file.exists():
                            await log(f"Previously Downloaded: {media.filename}", quiet=True)
                            self.files.skipped_files += 1
                            await self.SQL_Helper.mark_complete(url_path, original_filename)
                            progress.advance(album_task, 1)
                            return
                        else:
                            break
                    else:
                        media.filename = downloaded_filename
                        complete_file = (self.download_dir / album / media.filename)
                        partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                        continue
                else:
                    iterations = 1
                    while True:
                        filename = f"{complete_file.stem} ({iterations}){media.ext}"
                        iterations += 1
                        temp_complete_file = (self.download_dir / album / filename)
                        if not temp_complete_file.exists():
                            if not await self.SQL_Helper.check_filename(filename):
                                media.filename = filename
                                complete_file = (self.download_dir / album / media.filename)
                                partial_file = complete_file.with_suffix(complete_file.suffix + '.part')
                                break
                    break
            else:
                break

        await self.SQL_Helper.update_pre_download(complete_file, media.filename, url_path, original_filename)

        if self.mark_downloaded:
            await self.SQL_Helper.mark_complete(url_path, original_filename)

        resume_point = 0
        await self.SQL_Helper.sql_insert_temp(str(partial_file))
        range_num = None
        if partial_file.exists():
            resume_point = partial_file.stat().st_size
            range_num = f'bytes={resume_point}-'

        for key, value in self.delay.items():
            if key in media.url.host:
                current_throttle = value

        headers = {"Authorization": await basic_auth("Cyberdrop-DL", self.pixeldrain_api_key)} \
            if (self.pixeldrain_api_key and "pixeldrain" in media.url.host) else {}
        if range_num:
            headers['Range'] = range_num

        try:
            task_description = media.filename
            if len(task_description) >= 40:
                task_description = task_description[:37] + "..."
            else:
                task_description = task_description.rjust(40)
            file_task = progress.add_task("[plum3]"+task_description, progress_type="file")
            await self.download_session.download_file(media, partial_file, current_throttle, resume_point,
                                                      self.File_Lock, self.proxy, headers, original_filename,
                                                      progress, file_task)
            partial_file.rename(complete_file)
            await self.SQL_Helper.mark_complete(url_path, original_filename)
            if media.url.parts[-1] in self.current_attempt.keys():
                self.current_attempt.pop(media.url.parts[-1])
            self.files.completed_files += 1
            progress.advance(album_task, 1)
            progress.update(file_task, visible=False)
            await log(f"Completed Download: {media.filename}", quiet=True)
            await self.File_Lock.remove_lock(original_filename)

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientResponseError, DownloadFailure) as e:
            if await self.File_Lock.check_lock(original_filename):
                await self.File_Lock.remove_lock(original_filename)

            new_error = DownloadFailure(1)
            try:
                progress.update(file_task, visible=False)
            except:
                pass

            if hasattr(e, "message"):
                logging.debug(f"\n{media.url} ({e.message})")
                new_error.message = e.message

            if hasattr(e, "code"):
                if 400 <= e.code < 500 and e.code != 429:
                    logger.debug("We ran into a 400 level error: %s", str(e.code))
                    await log(f"Failed Download: {media.filename}", quiet=True)
                    self.files.failed_files += 1
                    progress.advance(album_task, 1)
                    if media.url.parts[-1] in self.current_attempt.keys():
                        self.current_attempt.pop(media.url.parts[-1])
                    return
                logger.debug("Error status code: " + str(e.code))
                new_error.code = e.code

            raise new_error


async def download_cascade(args: dict, Cascade: CascadeItem, SQL_Helper: SQLHelper, client: Client,
                           scraper: ScrapeMapper) -> None:
    user_threads = args["Runtime"]["simultaneous_downloads"]
    files = Files()

    with CascadeProgress() as progress:
        cascade_task = progress.add_task("[light_salmon3]Domains", progress_type="cascade", total=len(Cascade.domains))

        downloaders = []
        tasks = []
        for domain, domain_obj in Cascade.domains.items():
            threads = user_threads if user_threads != 0 else multiprocessing.cpu_count()
            if 'bunkr' in domain or 'pixeldrain' in domain or 'anonfiles' in domain:
                threads = 2 if (threads > 2) else threads
            download_semaphore = asyncio.Semaphore(threads)
            downloaders.append(Downloader(args, client, SQL_Helper, scraper, threads, domain, domain_obj, download_semaphore, files))
        for downloader in downloaders:
            tasks.append(downloader.start_domain(progress, cascade_task))
        await asyncio.gather(*tasks)

    await log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: {files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")


async def download_forums(args: dict, Forums: ForumItem, SQL_Helper: SQLHelper, client: Client,
                          scraper: ScrapeMapper) -> None:
    user_threads = args["Runtime"]["simultaneous_downloads"]
    files = Files()

    with ForumsProgress() as progress:
        forum_task = progress.add_task("[orange3]FORUM THREADS", progress_type="forum", total=len(Forums.threads))
        for title, Cascade in Forums.threads.items():
            cascade_task = progress.add_task("[light_salmon3]"+title.upper(), progress_type="cascade", total=len(Cascade.domains))

            downloaders = []
            tasks = []
            for domain, domain_obj in Cascade.domains.items():
                threads = user_threads if user_threads != 0 else multiprocessing.cpu_count()
                if 'bunkr' in domain or 'pixeldrain' in domain or 'anonfiles' in domain:
                    threads = 2 if (threads > 2) else threads
                download_semaphore = asyncio.Semaphore(threads)
                downloaders.append(Downloader(args, client, SQL_Helper, scraper, threads, domain, domain_obj, download_semaphore, files))
            for downloader in downloaders:
                tasks.append(downloader.start_domain(progress, cascade_task))
            await asyncio.gather(*tasks)

            progress.advance(forum_task, 1)
    await log("")
    await log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: {files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")

