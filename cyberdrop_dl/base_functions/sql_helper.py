from __future__ import annotations

import atexit
import logging
import sqlite3
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from pathlib import Path

    from yarl import URL

    from cyberdrop_dl.base_functions.data_classes import (
        AlbumItem,
        CascadeItem,
        DomainItem,
        MediaItem,
    )


async def get_db_path(url: URL, referer: str = "") -> str:
    """Gets the URL path to be put into the DB and checked from the DB"""
    url_path = url.path

    if url.host and ('anonfiles' in url.host or 'bayfiles' in url.host):
        url_parts = url_path.split('/')
        url_parts.pop(0)
        if len(url_parts) > 1:
            url_parts.pop(1)
        url_path = '/' + '/'.join(url_parts)

    if referer and "e-hentai" in referer:
        url_path = url_path.split('keystamp')[0][:-1]

    return url_path


class SQLHelper:
    """This class is responsible for handling SQL operations"""
    def __init__(self, ignore_history: bool, ignore_cache: bool, download_history: str):
        self.ignore_history = ignore_history
        self.ignore_cache = ignore_cache
        self.download_history = download_history
        self.conn = sqlite3.connect(self.download_history)
        self.curs = self.conn.cursor()

        self.old_history = False
        # Close the sql connection when the program exits
        atexit.register(self._exit_handler)

    async def sql_initialize(self) -> None:
        """Initializes the SQL connection, and makes sure necessary tables exist"""
        await self._check_old_history()
        await self._pre_allocate()
        await self._create_media_history()
        await self._create_coomeno_history()

    async def _check_old_history(self) -> None:
        """Checks whether V3 history exists"""
        try:
            self.curs.execute("""SELECT name FROM sqlite_schema WHERE type='table' AND name='downloads'""")
            sql_file_check = self.curs.fetchone()
        except Exception:
            self.curs.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'""")
            sql_file_check = self.curs.fetchone()
        if sql_file_check:
            self.old_history = True

    async def _create_media_history(self) -> None:
        """We create the download history tables here"""
        create_table_query = """CREATE TABLE IF NOT EXISTS media (
                                                    domain TEXT,
                                                    url_path TEXT,
                                                    album_path TEXT,
                                                    referer TEXT,
                                                    download_path TEXT,
                                                    download_filename TEXT,
                                                    original_filename TEXT,
                                                    completed INTEGER NOT NULL,
                                                    PRIMARY KEY (url_path, original_filename)
                                                );"""
        create_temp_download_name_query = """CREATE TABLE IF NOT EXISTS downloads_temp (
                                                                downloaded_filename TEXT
                                                            );"""
        temp_truncate_query = """DELETE FROM downloads_temp;"""

        self.curs.execute(create_table_query)
        self.conn.commit()
        self.curs.execute(create_temp_download_name_query)
        self.conn.commit()
        self.curs.execute(temp_truncate_query)
        self.conn.commit()

    async def _create_coomeno_history(self) -> None:
        """Creates the cache table for coomeno"""
        create_table_query = """CREATE TABLE IF NOT EXISTS coomeno (
                                                            url_path TEXT,
                                                            post_data BLOB,
                                                            PRIMARY KEY (url_path)
                                                        );"""
        self.curs.execute(create_table_query)
        self.conn.commit()

    async def _pre_allocate(self) -> None:
        """We pre-allocate 50MB of space to the SQL file just in case the user runs out of disk space"""
        pre_alloc = "CREATE TABLE IF NOT EXISTS t(x);"
        pre_alloc2 = "INSERT INTO t VALUES(zeroblob(50*1024*1024));"  # 50 mb
        drop_pre = "DROP TABLE t;"
        check_prealloc = "PRAGMA freelist_count;"

        self.curs.execute(check_prealloc)
        free = self.curs.fetchone()[0]
        if free <= 1024:
            self.curs.execute(pre_alloc)
            self.conn.commit()
            self.curs.execute(pre_alloc2)
            self.conn.commit()
            self.curs.execute(drop_pre)
            self.conn.commit()

    """Temp Table Operations"""

    async def get_temp_names(self) -> List[str]:
        """Gets the list of temp filenames"""
        self.curs.execute("SELECT downloaded_filename FROM downloads_temp;")
        filenames = self.curs.fetchall()
        return list(sum(filenames, ()))

    async def sql_insert_temp(self, downloaded_filename: str) -> None:
        """Inserts a temp filename into the downloads_temp table"""
        self.curs.execute("""INSERT OR IGNORE INTO downloads_temp VALUES (?)""", (downloaded_filename,))
        self.conn.commit()

    """Coomeno Table Operations"""

    async def insert_blob(self, blob: str, url: URL) -> None:
        """Inserts the post content into coomeno"""
        url_path = await get_db_path(url)
        self.curs.execute("""INSERT OR IGNORE INTO coomeno VALUES (?, ?)""", (url_path, blob))
        self.conn.commit()

    async def get_blob(self, url: URL) -> Optional[str]:
        """returns the post content for a given coomeno post url"""
        if self.ignore_cache:
            return None
        url_path = await get_db_path(url)
        self.curs.execute("""SELECT post_data FROM coomeno WHERE url_path = ?""", (url_path,))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            return sql_file_check[0]
        return None

    """Download Table Operations"""

    async def _insert_media(self, domain: str, album_path: str, media: MediaItem) -> None:
        """Inserts a media entry into the media table without commit"""
        url_path = await get_db_path(media.url, domain)
        self.curs.execute("""INSERT OR IGNORE INTO media VALUES (?, ?, ?, ?, '', '', ?, 0)""",
                          (domain, url_path, album_path, str(media.referer), media.original_filename))

    async def _insert_album(self, domain: str, album_path: str, album: AlbumItem) -> None:
        """Inserts an albums media into the media table without commit"""
        for media in album.media:
            await self._insert_media(domain, album_path, media)

    async def insert_media(self, domain: str, album_path: str, media: MediaItem) -> None:
        """Inserts a media entry into the media table"""
        await self._insert_media(domain, album_path, media)
        self.conn.commit()

    async def insert_album(self, domain: str, album_url: URL, album: AlbumItem) -> None:
        """Inserts an albums media into the media table"""
        if album.media:
            album_path = await get_db_path(album_url)
            await self._insert_album(domain, album_path, album)
            self.conn.commit()

    async def insert_domain(self, domain_name: str, album_url: URL, domain: DomainItem) -> None:
        """Inserts a domains media into the media table"""
        if domain.albums:
            album_path = await get_db_path(album_url)
            for album in domain.albums.values():
                await self._insert_album(domain_name, album_path, album)
            self.conn.commit()

    async def insert_cascade(self, cascade: CascadeItem) -> None:
        """Inserts a cascades media into the media table"""
        if not await cascade.is_empty():
            for domain, domain_obj in cascade.domains.items():
                for album_obj in domain_obj.albums.values():
                    for media in album_obj.media:
                        await self._insert_media(domain, media.referer.path, media)
            self.conn.commit()

    async def get_downloaded_filename(self, url_path: str, filename: str) -> Optional[str]:
        """Gets downloaded filename given the url path and original filename"""
        self.curs.execute("""SELECT download_filename FROM media WHERE url_path = ? and original_filename = ?""",
                          (url_path, filename))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            return sql_file_check[0]
        return None

    async def sql_check_old_existing(self, url_path: str) -> bool:
        """Checks the V3 history table for completed if it exists"""
        if not self.old_history or self.ignore_history:
            return False
        self.curs.execute("""SELECT completed FROM downloads WHERE path = ?""", (url_path,))
        sql_file_check = self.curs.fetchone()
        return sql_file_check and sql_file_check[0] == 1

    async def check_complete_singular(self, domain: str, url: URL) -> bool:
        """Checks whether an individual file has completed given its domain and url path"""
        if self.ignore_history:
            return False
        url_path = await get_db_path(url, domain)
        self.curs.execute("""SELECT completed FROM media WHERE domain = ? and url_path = ?""", (domain, url_path))
        sql_file_check = self.curs.fetchone()
        return sql_file_check and sql_file_check[0] != 0

    """Downloader Operations"""

    async def check_filename(self, filename: str) -> bool:
        """Checks whether an individual exists in the DB given its filename"""
        self.curs.execute("""SELECT EXISTS(SELECT 1 FROM media WHERE download_filename = ?)""", (filename, ))
        sql_check = self.curs.fetchone()[0]
        return sql_check == 1

    async def update_pre_download(self, path: Path, filename: str, url_path: str, original_filename: str) -> None:
        """Update the media entry pre-download"""
        self.curs.execute("""UPDATE media SET download_path = ?, download_filename = ? WHERE url_path = ? 
        AND original_filename = ?""", (str(path), filename, url_path, original_filename))
        self.conn.commit()

    async def mark_complete(self, url_path: str, original_filename: str) -> None:
        """Update the media entry post-download"""
        self.curs.execute("""UPDATE media SET completed = 1 WHERE url_path = ? AND original_filename = ?""", (url_path, original_filename))
        self.conn.commit()

    """DB Fixes"""
    async def fix_bunkr_entries(self, url: URL, original_filename: str) -> None:
        complete_row = None
        url_path = await get_db_path(url)
        self.curs.execute("""SELECT * FROM media WHERE url_path = ?""", (url_path,))
        sql_res = self.curs.fetchall()
        for row in sql_res:
            if row[7] == 1:
                if complete_row:
                    if row[6] == original_filename:
                        await self._remove_entry(url_path, complete_row[6])
                        complete_row = row
                    else:
                        await self._remove_entry(url_path, row[6])
                else:
                    complete_row = row
            else:
                if len(sql_res) < 2:
                    await self._update_row_original_filename(url_path, original_filename)
                    break
                await self._remove_entry(url_path, row[6])
        if complete_row and complete_row[6] != original_filename:
            await self._update_row_original_filename(url_path, original_filename)
        self.conn.commit()

    async def _update_row_original_filename(self, url_path: str, original_filename: str) -> None:
        self.curs.execute("""UPDATE media SET original_filename = ? WHERE url_path = ?""", (original_filename, url_path))
        self.conn.commit()

    async def _remove_entry(self, url_path: str, original_filename: str) -> None:
        self.curs.execute("""DELETE FROM media WHERE url_path = ? AND original_filename = ?""", (url_path, original_filename))
        self.conn.commit()

    def _exit_handler(self) -> None:
        """Exit handler on unexpected exits"""
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            logging.debug("Failed to close sqlite database connection: %s", e)
        else:
            logging.debug("Successfully closed sqlite database connection")
