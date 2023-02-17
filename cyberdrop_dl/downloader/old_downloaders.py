from __future__ import annotations

import asyncio
import logging
import multiprocessing
from base64 import b64encode
from functools import wraps
from random import gauss

import aiofiles
import aiohttp.client_exceptions
from tqdm import tqdm
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log, logger, check_free_space, allowed_filetype, get_db_path, \
    clear
from cyberdrop_dl.base_functions.error_classes import DownloadFailure
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.base_functions.data_classes import AlbumItem, CascadeItem, FileLock, ForumItem, DomainItem, MediaItem
from cyberdrop_dl.client.client import Client, DownloadSession
from cyberdrop_dl.scraper.Scraper import ScrapeMapper


async def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


def retry(f):
    """This function is a wrapper that handles retrying for failed downloads"""

    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except DownloadFailure as e:
                if not self.disable_attempt_limit:
                    if self.current_attempt[args[2]] >= self.allowed_attempts - 1:
                        await self.output_failed(args[1], e)
                        logger.debug('Skipping %s...', args[1].url, exc_info=True)
                        self.files.failed_files += 1
                        self.progress.update(1)
                        return
                logger.debug(e.message)
                logger.debug(f'Retrying ({self.current_attempt[args[2]]}) {args[1].url}...')
                self.current_attempt[args[2]] += 1

    return wrapper


class Files:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self):
        self.completed_files = 0
        self.skipped_files = 0
        self.failed_files = 0


class Old_Downloader:
    """Downloader class, directs downloading for domain objects"""

    def __init__(self, args: dict, client: Client, SQL_Helper: SQLHelper, scraper: ScrapeMapper, max_workers: int,
                 domain: str, domain_obj: DomainItem, semaphore: asyncio.Semaphore, files: Files, progress: tqdm):
        self.backup_scraper = scraper
        self.client = client
        self.download_session = DownloadSession(client)
        self.File_Lock = FileLock()
        self.SQL_Helper = SQL_Helper

        self.domain = domain
        self.domain_obj = domain_obj

        self.errored_output = args['Runtime']['output_errored_urls']
        self.errored_file = args['Files']['errored_urls_file']

        self.files = files
        self.progress = progress

        self.current_attempt = {}
        self.max_workers = max_workers
        self._semaphore = semaphore
        self.delay = {'cyberfile': 1, 'anonfiles': 1, "coomer": 0.2, "kemono": 0.2}

        self.pixeldrain_api_key = args["Authentication"]["pixeldrain_api_key"]

        self.ignore_history = args["Ignore"]["ignore_history"]
        self.exclude_audio = args["Ignore"]["exclude_audio"]
        self.exclude_images = args["Ignore"]["exclude_images"]
        self.exclude_videos = args["Ignore"]["exclude_videos"]
        self.exclude_other = args["Ignore"]["exclude_other"]

        self.block_sub_folders = args['Runtime']['block_sub_folders']
        self.allowed_attempts = args["Runtime"]["attempts"]
        self.allow_insecure_connections = args["Runtime"]["allow_insecure_connections"]
        self.disable_attempt_limit = args["Runtime"]["disable_attempt_limit"]
        self.download_dir = args["Files"]["output_folder"]
        self.mark_downloaded = args["Runtime"]["skip_download_mark_completed"]
        self.proxy = args["Runtime"]["proxy"]
        self.required_free_space = args["Runtime"]["required_free_space"]

    async def start_domain(self):
        """Handler for domains and the progress bars for it"""
        for album, album_obj in self.domain_obj.albums.items():
            await self.start_album(album, album_obj)
        await self.download_session.exit_handler()

    async def start_album(self, album: str, album_obj: AlbumItem):
        """Handler for albums and the progress bars for it"""
        if await album_obj.is_empty():
            return
        download_tasks = []
        for media in album_obj.media:
            download_tasks.append(self.start_file(album, media))
        await asyncio.gather(*download_tasks)

    async def start_file(self, album: str, media: MediaItem):
        """Handler for files and the progress bars for it"""
        if media.complete:
            await log(f"Previously Downloaded: {media.filename}", quiet=True)
            self.files.skipped_files += 1
            self.progress.update(1)
            return
        else:
            url_path = await get_db_path(URL(media.url), self.domain)
            complete = await self.SQL_Helper.check_complete_singular(self.domain, url_path)
            if complete:
                await log(f"Previously Downloaded: {media.filename}", quiet=True)
                self.files.skipped_files += 1
                self.progress.update(1)
                return
        async with self._semaphore:
            url_path = await get_db_path(URL(media.url), self.domain)
            await self.download_file(album, media, url_path)

    @retry
    async def download_file(self, album: str, media: MediaItem, url_path: str):
        """File downloader"""
        if not await check_free_space(self.required_free_space, self.download_dir):
            await log("We've run out of free space.", quiet=True)
            self.files.skipped_files += 1
            self.progress.update(1)
            return

        if not await allowed_filetype(media, self.exclude_images, self.exclude_videos, self.exclude_audio,
                                      self.exclude_other):
            await log(f"Blocked by file extension: {media.filename}", quiet=True)
            self.files.skipped_files += 1
            self.progress.update(1)
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
            if media.url.parts[-1] in self.current_attempt.keys():
                self.current_attempt.pop(media.url.parts[-1])

            if fake_download:
                self.files.skipped_files += 1
                self.progress.update(1)
            else:
                self.files.completed_files += 1
                self.progress.update(1)

            await log(f"Completed Download: {media.filename} from {media.referer}", quiet=True)
            await self.File_Lock.remove_lock(original_filename)
            return

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.ServerTimeoutError,
                DownloadFailure, PermissionError) as e:
            if await self.File_Lock.check_lock(original_filename):
                await self.File_Lock.remove_lock(original_filename)

            new_error = DownloadFailure(code=1)

            if hasattr(e, "message"):
                logging.debug(f"\n{media.url} ({e.message})")
            new_error.message = repr(e)

            if hasattr(e, "code"):
                if 400 <= e.code < 500 and e.code != 429:
                    logger.debug("We ran into a 400 level error: %s", str(e.code))
                    await log(f"Failed Download: {media.filename}", quiet=True)
                    self.files.failed_files += 1
                    self.progress.update(1)
                    if url_path in self.current_attempt.keys():
                        self.current_attempt.pop(url_path)
                    await self.output_failed(media, e)
                    return
                logger.debug("Error status code: " + str(e.code))
                new_error.code = e.code

            raise new_error

    async def output_failed(self, media, e):
        if self.errored_output:
            async with aiofiles.open(self.errored_file, mode='a') as file:
                await file.write(f"{media.url},{media.referer},{e.message}\n")

    async def check_file_exists(self, complete_file, partial_file, media, album, url_path, original_filename,
                                current_throttle):
        """Complicated checker for if a file already exists, and was already downloaded"""
        expected_size = None
        proceed = True
        while True:
            if complete_file.exists() or partial_file.exists():
                if not expected_size:
                    expected_size = await self.download_session.get_filesize(media.url, str(media.referer),
                                                                             current_throttle)
                if complete_file.exists():
                    if complete_file.stat().st_size == expected_size:
                        proceed = False
                        break
                downloaded_filename = await self.SQL_Helper.get_downloaded_filename(url_path, original_filename)
                if downloaded_filename:
                    if media.filename == downloaded_filename:
                        if complete_file.exists():
                            proceed = False
                            break
                        elif partial_file.exists():
                            if partial_file.stat().st_size == expected_size:
                                proceed = False
                                partial_file.rename(complete_file)
                                break
                            else:
                                break
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
        return complete_file, partial_file, proceed


async def old_download_cascade(args: dict, Cascade: CascadeItem, SQL_Helper: SQLHelper, client: Client,
                               scraper: ScrapeMapper) -> None:
    """Handler for cascades and the progress bars for it"""
    user_threads = args["Runtime"]["simultaneous_downloads_per_domain"]

    files = Files()

    downloaders = []
    tasks = []
    total_files = await Cascade.get_total()
    with tqdm(total=total_files, unit_scale=True, unit='Files', leave=True, initial=0,
              desc="Files Downloaded") as progress:
        for domain, domain_obj in Cascade.domains.items():
            threads = user_threads if user_threads != 0 else multiprocessing.cpu_count()
            if 'bunkr' in domain or 'pixeldrain' in domain or 'anonfiles' in domain:
                threads = 2 if (threads > 2) else threads
            download_semaphore = asyncio.Semaphore(threads)
            downloaders.append(Old_Downloader(args, client, SQL_Helper, scraper, threads, domain, domain_obj,
                                              download_semaphore, files, progress))
        for downloader in downloaders:
            tasks.append(downloader.start_domain())
        await asyncio.gather(*tasks)

    await clear()
    await log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: "
              f"{files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")


async def old_download_forums(args: dict, Forums: ForumItem, SQL_Helper: SQLHelper, client: Client,
                              scraper: ScrapeMapper) -> None:
    """Handler for forum threads and the progress bars for it"""
    user_threads = args["Runtime"]["simultaneous_downloads_per_domain"]

    files = Files()
    total_files = await Forums.get_total()
    with tqdm(total=total_files, unit_scale=True, unit='Files', leave=True, initial=0,
              desc="Files Downloaded") as progress:
        for title, Cascade in Forums.threads.items():
            downloaders = []
            tasks = []

            for domain, domain_obj in Cascade.domains.items():
                threads = user_threads if user_threads != 0 else multiprocessing.cpu_count()
                if 'bunkr' in domain or 'pixeldrain' in domain or 'anonfiles' in domain:
                    threads = 2 if (threads > 2) else threads
                download_semaphore = asyncio.Semaphore(threads)
                downloaders.append(Old_Downloader(args, client, SQL_Helper, scraper, threads, domain, domain_obj,
                                                  download_semaphore, files, progress))
            for downloader in downloaders:
                tasks.append(downloader.start_domain())
            await asyncio.gather(*tasks)

    await clear()
    await log(f"| [green]Files Complete: {files.completed_files}[/green] - [yellow]Files Skipped: "
              f"{files.skipped_files}[/yellow] - [red]Files Failed: {files.failed_files}[/red] |")
