import asyncio
import logging
import multiprocessing
import time
import traceback
from functools import wraps
from pathlib import Path
from typing import List, Optional, Tuple
from random import gauss

import aiofiles
import aiofiles.os
import aiohttp.client_exceptions
from colorama import Fore
from tqdm import tqdm
from yarl import URL

from .base_functions import FILE_FORMATS, MAX_FILENAME_LENGTH, log, logger, sanitize, ssl_context, user_agent
from .sql_helper import SQLHelper
from .data_classes import AlbumItem, CascadeItem, FileLock


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""
    pass


def retry(f):
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except FailureException:
                if not self.disable_attempt_limit:
                    if self.current_attempt >= self.attempts - 1:
                        raise
                logger.debug('Retrying %s...' % args[0])
                self.attempts += 1
                await asyncio.sleep(2)
    return wrapper


async def throttle(self, delay, host) -> None:
    if delay is None:
        return

    key: Optional[str] = None
    while True:
        if key is None:
            key = 'throttle:{}'.format(host)
        now = time.time()
        last = self.throttle_times.get(key, 0.0)
        elapsed = now - last

        if elapsed >= delay:
            self.throttle_times[key] = now
            return

        remaining = delay - elapsed + 0.25

        log_string = '\nDelaying request to %s for %.2f seconds.' % (
            host, remaining)
        logger.debug(log_string)
        await asyncio.sleep(remaining)


class Downloader:
    def __init__(self, album_obj: AlbumItem, cookie_jar, folder: Path, title: str, attempts: int,
                 disable_attempt_limit: bool, max_workers: int, exclude_videos: bool, exclude_images: bool,
                 exclude_audio: bool, exclude_other: bool, SQL_helper: SQLHelper):
        self.album_obj = album_obj
        self.cookie_jar = cookie_jar
        self.folder = folder
        self.title = title

        self.SQL_helper = SQL_helper
        self.File_Lock = FileLock()

        self.attempts = attempts
        self.current_attempt = 0
        self.disable_attempt_limit = disable_attempt_limit

        self.exclude_videos = exclude_videos
        self.exclude_images = exclude_images
        self.exclude_audio = exclude_audio
        self.exclude_other = exclude_other

        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self.delay = {'cyberfile.is': 1}
        self.throttle_times = {}

    """Changed from aiohttp exceptions caught to FailureException to allow for partial downloads."""

    @retry
    async def download_file(
            self,
            url: URL,
            referral: URL,
            filename: str,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL"""
        headers = {'Referer': str(referral), 'user-agent': user_agent}

        # return if completed already
        if await self.SQL_helper.sql_check_existing(url.path):
            logger.debug(msg=f"{url.path} found in DB: Skipping {filename}")
            return

        try:
            async with self._semaphore:
                # If ext isn't allowable we likely have an invalid filename, lets go get it.
                ext = '.' + filename.split('.')[-1].lower()
                if not (ext in FILE_FORMATS['Images'] or ext in FILE_FORMATS['Videos'] or ext in FILE_FORMATS['Audio'] or ext in FILE_FORMATS['Other']):
                    for key, value in self.delay.items():
                        if key in url.host:
                            await throttle(self, value, key)
                    async with session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True) as resp:
                        try:
                            filename = resp.content_disposition.filename
                            filename = await sanitize(filename)
                        except:
                            await log("\nCouldn't get filename for: " + str(url))
                            return

                # Make suffix always lower case
                ext = '.' + filename.split('.')[-1].lower()
                filename = filename.replace('.' + filename.split('.')[-1], ext)

                # Skip based on CLI arg.
                if self.exclude_videos:
                    if ext in FILE_FORMATS['Videos']:
                        logging.debug("Skipping " + filename)
                        return
                if self.exclude_images:
                    if ext in FILE_FORMATS['Images']:
                        logging.debug("Skipping " + filename)
                        return
                if self.exclude_audio:
                    if ext in FILE_FORMATS['Audio']:
                        logging.debug("Skipping " + filename)
                        return
                if self.exclude_other:
                    if ext in FILE_FORMATS['Other']:
                        logging.debug("Skipping " + filename)
                        return

                original_filename = filename
                while await self.File_Lock.check_lock(filename):
                    await asyncio.sleep(gauss(1, 1.5))
                await self.File_Lock.add_lock(filename)

                complete_file = (self.folder / self.title / filename)
                partial_file = (self.folder / self.title / filename)

                if complete_file.exists() or partial_file.exists():
                    if complete_file.exists():
                        async with session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True) as resp:
                            total_size = int(resp.headers.get('Content-Length', str(0)))
                        if complete_file.stat().st_size == total_size:
                            await self.SQL_helper.sql_insert_file(url.path, complete_file.name, 1)
                            logger.debug("\nFile already exists and matches expected size: " + str(complete_file))
                            return

                    download_name = await self.SQL_helper.get_download_filename(url.path)
                    iterations = 1

                    if not download_name:
                        while True:
                            filename = complete_file.stem + " (%d)" % iterations + ext
                            iterations += 1
                            temp_complete_file = (self.folder / self.title / filename)
                            if not temp_complete_file.exists():
                                if not await self.SQL_helper.check_filename(filename):
                                    break
                    else:
                        filename = download_name

                await self.SQL_helper.sql_insert_file(url.path, filename, 0)

                complete_file = (self.folder / self.title / filename)
                resume_point = 0
                temp_file = complete_file.with_suffix(complete_file.suffix + '.part')

                if temp_file.exists():
                    resume_point = temp_file.stat().st_size
                    headers['Range'] = 'bytes=%d-' % resume_point

                for key, value in self.delay.items():
                    if key in url.host:
                        await throttle(self, value, key)

                async with session.get(url, headers=headers, ssl=ssl_context, raise_for_status=True) as resp:
                    content_type = resp.headers.get('Content-Type')
                    if 'text' in content_type.lower() or 'html' in content_type.lower():
                        logger.debug(f"Server for %s is either down or the file no longer exists" % str(url))
                        await self.File_Lock.remove_lock(original_filename)
                        return

                    total = int(resp.headers.get('Content-Length', str(0))) + resume_point
                    (self.folder / self.title).mkdir(parents=True, exist_ok=True)

                    with tqdm(
                            total=total, unit_scale=True,
                            unit='B', leave=False, initial=resume_point,
                            desc=filename, disable=(not show_progress)
                    ) as progress:
                        async with aiofiles.open(temp_file, mode='ab') as f:
                            async for chunk, _ in resp.content.iter_chunks():
                                await asyncio.sleep(0)
                                await f.write(chunk)
                                progress.update(len(chunk))
            await self.rename_file(filename, url)
            await self.File_Lock.remove_lock(original_filename)

        except (aiohttp.client_exceptions.ClientPayloadError, aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientResponseError, FailureException) as e:
            try:
                await self.File_Lock.remove_lock(original_filename)
            except:
                pass

            logger.debug(e)

            try:
                logger.debug("Error status code: " + str(e.code))
                if 400 <= e.code < 500 and e.code != 429:
                    logger.debug("We ran into a 400 level error: %s" % str(e.code))
                    return
                resp.close()
            except Exception as e2:
                pass

            raise FailureException(e)

    async def rename_file(self, filename: str, url: URL) -> None:
        """Rename complete file."""
        complete_file = (self.folder / self.title / filename)
        temp_file = complete_file.with_suffix(complete_file.suffix + '.part')
        if complete_file.exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
            await aiofiles.os.remove(temp_file)
        else:
            temp_file.rename(complete_file)

        await self.SQL_helper.sql_update_file(url.path, filename, 1)
        logger.debug("Finished " + filename)

    async def download_and_store(
            self,
            url_tuple: Tuple,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the content of given URL and store it in a file."""
        url, referral = url_tuple

        filename = url.name
        filename = await sanitize(filename)
        if "v=" in filename:
            filename = filename.split('v=')[0]
        if len(filename) > MAX_FILENAME_LENGTH:
            fileext = filename.split('.')[-1]
            filename = filename[:MAX_FILENAME_LENGTH] + '.' + fileext

        logger.debug("Working on " + str(url))
        try:
            await self.download_file(url, referral=referral, filename=filename, session=session,
                                     show_progress=show_progress)
        except Exception:
            logger.debug(traceback.format_exc())
            await log(f"\nError attempting {filename}: See downloader.log for details\n", Fore.WHITE)

    async def download_all(
            self,
            album_obj: AlbumItem,
            session: aiohttp.ClientSession,
            show_progress: bool = True
    ) -> None:
        """Download the data from all given links and store them into corresponding files."""
        coros = [self.download_and_store(url_object, session, show_progress)
                 for url_object in album_obj.link_pairs]
        for func in tqdm(asyncio.as_completed(coros), total=len(coros), desc=self.title, unit='FILES'):
            await func

    async def download_content(self, show_progress: bool = True) -> None:
        """Download the content of all links and save them as files."""
        async with aiohttp.ClientSession(cookie_jar=self.cookie_jar) as session:
            await self.download_all(self.album_obj, session, show_progress=show_progress)
        self.SQL_helper.conn.commit()


async def get_downloaders(Cascade: CascadeItem, folder: Path, attempts: int, disable_attempt_limit: bool, threads: int,
                    exclude_videos: bool, exclude_images: bool, exclude_audio: bool, exclude_other: bool,
                    SQL_helper: SQLHelper) -> List[Downloader]:
    """Get a list of downloaders for each supported type of URLs.
    We shouldn't just assume that each URL will have the same netloc as
    the first one, so we need to classify them one by one, sort them to
    corresponding netloc URLs and create downloaders separately for individual
    netloc URLs they support.
    """

    downloaders = []

    cookie_jar = Cascade.cookies

    for domain, domain_obj in Cascade.domains.items():
        max_workers = threads if threads != 0 else multiprocessing.cpu_count()
        if 'bunkr' in domain:
            max_workers = 3 if (max_workers > 3) else max_workers
        for title, album_obj in domain_obj.albums.items():
            downloader = Downloader(album_obj, cookie_jar=cookie_jar, title=title, folder=folder,
                                    attempts=attempts, disable_attempt_limit=disable_attempt_limit,
                                    max_workers=max_workers, exclude_videos=exclude_videos,
                                    exclude_images=exclude_images, exclude_audio=exclude_audio,
                                    exclude_other=exclude_other, SQL_helper=SQL_helper)
            downloaders.append(downloader)
    return downloaders
