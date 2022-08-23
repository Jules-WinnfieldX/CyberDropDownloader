import asyncio
import logging
import traceback
from functools import wraps
from pathlib import Path
from typing import List, Tuple, Dict
from random import gauss

import aiofiles
import aiofiles.os
import aiohttp.client_exceptions
from tqdm import tqdm
from yarl import URL

from ..base_functions.base_functions import FILE_FORMATS, MAX_FILENAME_LENGTH, log, logger, sanitize
from ..base_functions.sql_helper import SQLHelper
from ..base_functions.data_classes import AlbumItem, CascadeItem, FileLock
from ..client.client import Client, DownloadSession


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""


def retry(f):
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        while True:
            try:
                return await f(self, *args, **kwargs)
            except FailureException:
                if not self.disable_attempt_limit:
                    if self.current_attempt[str(args[0])] >= self.attempts - 1:
                        logger.debug('Skipping %s...', args[0])
                        raise
                logger.debug(f'Retrying ({self.current_attempt[str(args[0])]}) {args[0]}...')
                self.current_attempt[str(args[0])] += 1

                if 'cyberdrop' in args[0].host:
                    ext = '.'+args[0].name.split('.')[-1]
                    if ext in FILE_FORMATS['Images']:
                        args = list(args)
                        args[0] = args[0].with_host('img-01.cyberdrop.to')
                        args = tuple(args)
                    else:
                        args = list(args)
                        args[0] = URL(str(args[0]).replace('fs-05.', 'fs-04.'))
                        args = tuple(args)
                await asyncio.sleep(2)
    return wrapper


class Downloader:
    def __init__(self, album_obj: AlbumItem, folder: Path, title: str, attempts: int,
                 disable_attempt_limit: bool, max_workers: int, excludes: Dict[str, bool], SQL_helper: SQLHelper,
                 client: Client):
        self.album_obj = album_obj
        self.client = client
        self.folder = folder
        self.title = title

        self.SQL_helper = SQL_helper
        self.File_Lock = FileLock()

        self.attempts = attempts
        self.current_attempt = {}
        self.disable_attempt_limit = disable_attempt_limit

        self.excludes = excludes

        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self.delay = {'cyberfile.is': 1, 'anonfiles.com': 1}

    """Changed from aiohttp exceptions caught to FailureException to allow for partial downloads."""

    @retry
    async def download_file(self, url: URL, referral: URL, filename: str, session: DownloadSession,
                            show_progress: bool = True) -> None:
        """Download the content of given URL"""
        if str(url) not in self.current_attempt:
            self.current_attempt[str(url)] = 0

        referer = str(referral)
        db_path = url.path

        if 'anonfiles' in url.host:
            db_path = db_path.split('/')
            db_path.pop(0)
            db_path.pop(1)
            db_path = '/'+'/'.join(db_path)

        # return if completed already
        if await self.SQL_helper.sql_check_existing(db_path):
            logger.debug(msg=f"{db_path} found in DB: Skipping {filename}")
            return

        try:
            async with self._semaphore:
                # If ext isn't allowable we likely have an invalid filename, lets go get it.
                ext = '.' + filename.split('.')[-1].lower()
                current_throttle = self.client.throttle
                if not (ext in FILE_FORMATS['Images'] or ext in FILE_FORMATS['Videos'] or
                        ext in FILE_FORMATS['Audio'] or ext in FILE_FORMATS['Other']):
                    for key, value in self.delay.items():
                        if key in url.host:
                            if value > current_throttle:
                                current_throttle = value
                    try:
                        filename = await session.get_filename(url, referer, current_throttle)
                        filename = await sanitize(filename)
                        ext = '.' + filename.split('.')[-1].lower()
                        if not (ext in FILE_FORMATS['Images'] or ext in FILE_FORMATS['Videos'] or ext in FILE_FORMATS['Audio'] or ext in FILE_FORMATS['Other']):
                            return
                    except:
                        try:
                            content_type = await session.get_content_type(url, referer, current_throttle)
                            if "image" in content_type:
                                ext_temp = content_type.split('/')[-1]
                                filename = filename + '.' + ext_temp
                                filename = await sanitize(filename)
                            else:
                                await log("Unhandled content_type for checking filename: " + content_type)
                                raise
                        except:
                            await log("\nCouldn't get filename for: " + str(url))
                            return

                # Make suffix always lower case
                ext = '.' + filename.split('.')[-1].lower()
                filename = filename.replace('.' + filename.split('.')[-1], ext)

                # Skip based on CLI arg.
                if self.excludes['videos']:
                    if ext in FILE_FORMATS['Videos']:
                        logging.debug("Skipping " + filename)
                        return
                if self.excludes['images']:
                    if ext in FILE_FORMATS['Images']:
                        logging.debug("Skipping " + filename)
                        return
                if self.excludes['audio']:
                    if ext in FILE_FORMATS['Audio']:
                        logging.debug("Skipping " + filename)
                        return
                if self.excludes['other']:
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
                        total_size = await session.get_filesize(url, referer, current_throttle)
                        if complete_file.stat().st_size == total_size:
                            await self.SQL_helper.sql_insert_file(db_path, complete_file.name, 1)
                            logger.debug("\nFile already exists and matches expected size: " + str(complete_file))
                            return

                    download_name = await self.SQL_helper.get_download_filename(db_path)
                    iterations = 1

                    if not download_name:
                        while True:
                            filename = f"{complete_file.stem} ({iterations}){ext}"
                            iterations += 1
                            temp_complete_file = (self.folder / self.title / filename)
                            if not temp_complete_file.exists():
                                if not await self.SQL_helper.check_filename(filename):
                                    break
                    else:
                        filename = download_name

                await self.SQL_helper.sql_insert_file(db_path, filename, 0)

                complete_file = (self.folder / self.title / filename)
                resume_point = 0
                temp_file = complete_file.with_suffix(complete_file.suffix + '.part')

                range = None
                if temp_file.exists():
                    resume_point = temp_file.stat().st_size
                    range = f'bytes={resume_point}-'

                for key, value in self.delay.items():
                    if key in url.host:
                        current_throttle = value

                await session.download_file(url, referer, current_throttle, range, original_filename, filename,
                                            temp_file, resume_point, show_progress, self.File_Lock, self.folder,
                                            self.title)

            await self.rename_file(filename, url, db_path)
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
                    logger.debug("We ran into a 400 level error: %s", str(e.code))
                    if 'media-files.bunkr' in url.host:
                        pass
                    else:
                        return
            except Exception:
                pass

            raise FailureException(e)

    async def rename_file(self, filename: str, url: URL, db_path: str) -> None:
        """Rename complete file."""
        complete_file = (self.folder / self.title / filename)
        temp_file = complete_file.with_suffix(complete_file.suffix + '.part')
        if complete_file.exists():
            logger.debug(str(self.folder / self.title / filename) + " Already Exists")
            await aiofiles.os.remove(temp_file)
        else:
            temp_file.rename(complete_file)

        await self.SQL_helper.sql_update_file(db_path, filename, 1)
        logger.debug("Finished " + filename)

    async def download_and_store(self, url_tuple: Tuple, session: DownloadSession, show_progress: bool = True) -> None:
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
            await log(f"\nError attempting {filename}: See downloader.log for details\n")

    async def download_all(self, album_obj: AlbumItem, session: DownloadSession, show_progress: bool = True) -> None:
        """Download the data from all given links and store them into corresponding files."""
        coros = [self.download_and_store(url_object, session, show_progress)
                 for url_object in album_obj.link_pairs]
        for func in tqdm(asyncio.as_completed(coros), total=len(coros), desc=self.title, unit='FILES'):
            await func

    async def download_content(self, show_progress: bool = True) -> None:
        """Download the content of all links and save them as files."""
        session = DownloadSession(self.client)
        await self.download_all(self.album_obj, session, show_progress=show_progress)
        self.SQL_helper.conn.commit()


async def get_downloaders(Cascade: CascadeItem, folder: Path, attempts: int, disable_attempt_limit: bool,
                          max_workers: int, excludes: Dict[str, bool], SQL_helper: SQLHelper, client: Client) -> List[Downloader]:
    """Get a list of downloaders for each supported type of URLs.
    We shouldn't just assume that each URL will have the same netloc as
    the first one, so we need to classify them one by one, sort them to
    corresponding netloc URLs and create downloaders separately for individual
    netloc URLs they support.
    """

    downloaders = []

    for domain, domain_obj in Cascade.domains.items():
        max_workers_temp = max_workers
        if 'bunkr' in domain or 'pixeldrain' in domain or 'anonfiles' in domain:
            max_workers_temp = 2 if (max_workers > 2) else max_workers
        for title, album_obj in domain_obj.albums.items():
            downloader = Downloader(album_obj, title=title, folder=folder, attempts=attempts,
                                    disable_attempt_limit=disable_attempt_limit, max_workers=max_workers_temp,
                                    excludes=excludes, SQL_helper=SQL_helper, client=client)
            downloaders.append(downloader)
    return downloaders
