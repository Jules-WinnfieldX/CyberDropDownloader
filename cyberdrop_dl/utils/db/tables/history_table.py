from __future__ import annotations

import aiosqlite
from typing import TYPE_CHECKING
from yarl import URL

from cyberdrop_dl.utils.db.table_definitions import create_history

if TYPE_CHECKING:
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


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


class HistoryTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn
        self.ignore_history: bool = False

    async def startup(self) -> None:
        """Startup process for the HistoryTable"""
        await self.db_conn.execute(create_history)
        await self.db_conn.commit()

    async def check_complete(self, domain: str, url: URL) -> bool:
        """Checks whether an individual file has completed given its domain and url path"""
        if self.ignore_history:
            return False
        url_path = await get_db_path(url, domain)
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT completed FROM media WHERE domain = ? and url_path = ?""", (domain, url_path))
        sql_file_check = await result.fetchone()
        return sql_file_check and sql_file_check[0] != 0

    async def insert_uncompleted(self, domain: str, media_item: MediaItem) -> None:
        """Inserts an uncompleted file into the database"""
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        await self.db_conn.execute("""INSERT OR IGNORE INTO media (domain, url_path, referer, original_filename, completed) VALUES (?, ?, ?, ?, ?)""", (domain, url_path, str(media_item.referer), media_item.original_filename, 0))
        await self.db_conn.commit()

    async def mark_complete(self, domain: str, media_item: MediaItem) -> None:
        """Mark a download as completed in the database"""
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        download_filename = media_item.download_filename if isinstance(media_item.download_filename, str) else ""
        await self.db_conn.execute("""UPDATE media SET completed = 1, download_filename = ? WHERE domain = ? and url_path = ?""", (download_filename, domain, url_path))
        await self.db_conn.commit()

    async def check_filename_exists(self, filename: str):
        """Checks whether a downloaded filename exists in the database"""
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT EXISTS(SELECT 1 FROM media WHERE download_filename = ?)""", (filename,))
        sql_file_check = await result.fetchone()
        return sql_file_check == 1

    async def get_downloaded_filename(self, domain: str, media_item: MediaItem):
        """Returns the downloaded filename from the database"""
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT downloaded_filename FROM media WHERE domain = ? and url_path = ?""", (domain, url_path))
        sql_file_check = await result.fetchone()
        return sql_file_check[0] if sql_file_check else None
