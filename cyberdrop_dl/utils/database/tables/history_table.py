from __future__ import annotations

from sqlite3 import Row

import aiosqlite
from typing import TYPE_CHECKING, Iterable
from yarl import URL

from cyberdrop_dl.utils.database.table_definitions import create_history, create_fixed_history

if TYPE_CHECKING:
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem, ScrapeItem


async def get_db_path(url: URL, referer: str = "") -> str:
    """Gets the URL path to be put into the DB and checked from the DB"""
    url_path = url.path

    if referer and "e-hentai" in referer:
        url_path = url_path.split('keystamp')[0][:-1]

    if referer and "mediafire" in referer:
        url_path = url.name

    return url_path


async def get_db_domain(domain: str) -> str:
    """Gets the domain to be put into the DB and checked from the DB"""
    if domain in ("img.kiwi", "jpg.church", "jpg.homes", "jpg.fish", "jpg.fishing", "jpg.pet", "jpeg.pet", "jpg1.su",
                  "jpg2.su", "jpg3.su"):
        domain = "sharex"
    return domain


class HistoryTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn
        self.ignore_history: bool = False

    async def startup(self) -> None:
        """Startup process for the HistoryTable"""
        await self.db_conn.execute(create_history)
        await self.db_conn.commit()
        await self.fix_primary_keys()
        await self.fix_bunkr_v4_entries()

    async def check_complete(self, domain: str, url: URL, referer: URL) -> bool:
        """Checks whether an individual file has completed given its domain and url path"""
        if self.ignore_history:
            return False

        domain = await get_db_domain(domain)

        url_path = await get_db_path(url, domain)
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT referer, completed FROM media WHERE domain = ? and url_path = ?""", (domain, url_path))
        sql_file_check = await result.fetchone()
        if sql_file_check and sql_file_check[1] != 0:
            # Update the referer if it has changed so that check_complete_by_referer can work
            if str(referer) != sql_file_check[0]:
                await cursor.execute("""UPDATE media SET referer = ? WHERE domain = ? and url_path = ?""", (str(referer), domain, url_path))
                await self.db_conn.commit()
            return True
        return False

    async def check_complete_by_referer(self, domain: str, referer: URL) -> bool:
        """Checks whether an individual file has completed given its domain and url path"""
        if self.ignore_history:
            return False

        domain = await get_db_domain(domain)
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT completed FROM media WHERE domain = ? and referer = ?""", (domain, str(referer)))
        sql_file_check = await result.fetchone()
        return sql_file_check and sql_file_check[0] != 0

    async def insert_incompleted(self, domain: str, media_item: MediaItem) -> None:
        """Inserts an uncompleted file into the database"""
        domain = await get_db_domain(domain)
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        download_filename = media_item.download_filename if isinstance(media_item.download_filename, str) else ""
        await self.db_conn.execute(
            """UPDATE media SET domain = ? WHERE domain = 'no_crawler' and url_path = ? and referer = ?""",
            (domain, url_path, str(media_item.referer)))
        await self.db_conn.execute(
            """INSERT OR IGNORE INTO media (domain, url_path, referer, download_path, download_filename, original_filename, completed) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (domain, url_path, str(media_item.referer), str(media_item.download_folder), download_filename,
             media_item.original_filename, 0))
        await self.db_conn.execute("""UPDATE media SET download_filename = ? WHERE domain = ? and url_path = ?""",
                                   (download_filename, domain, url_path))
        await self.db_conn.commit()

    async def mark_complete(self, domain: str, media_item: MediaItem) -> None:
        """Mark a download as completed in the database"""
        domain = await get_db_domain(domain)
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        await self.db_conn.execute("""UPDATE media SET completed = 1 WHERE domain = ? and url_path = ?""",
                                   (domain, url_path))
        await self.db_conn.commit()

    async def check_filename_exists(self, filename: str) -> bool:
        """Checks whether a downloaded filename exists in the database"""
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT EXISTS(SELECT 1 FROM media WHERE download_filename = ?)""", (filename,))
        sql_file_check = await result.fetchone()
        return sql_file_check == 1

    async def get_downloaded_filename(self, domain: str, media_item: MediaItem) -> str:
        """Returns the downloaded filename from the database"""
        domain = await get_db_domain(domain)
        url_path = await get_db_path(media_item.url, str(media_item.referer))
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT download_filename FROM media WHERE domain = ? and url_path = ?""",
                                      (domain, url_path))
        sql_file_check = await result.fetchone()
        return sql_file_check[0] if sql_file_check else None

    async def get_failed_items(self) -> Iterable[Row]:
        """Returns a list of failed items"""
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT * FROM media WHERE completed = 0""")
        failed_files = await result.fetchall()
        return failed_files

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fix_bunkr_v4_entries(self) -> None:
        """Fixes bunkr v4 entries in the database"""
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""SELECT * from media WHERE domain = 'bunkr' and completed = 1""")
        bunkr_entries = await result.fetchall()

        fixed_entries = []
        for entry in bunkr_entries:
            entry = list(entry)
            entry[0] = "bunkrr"
            await self.db_conn.execute("""INSERT or REPLACE INTO media VALUES (?, ?, ?, ?, ?, ?, ?)""", entry)
        await self.db_conn.commit()

        await self.db_conn.execute("""DELETE FROM media WHERE domain = 'bunkr'""")
        await self.db_conn.commit()

    async def fix_primary_keys(self) -> None:
        cursor = await self.db_conn.cursor()
        result = await cursor.execute("""pragma table_info(media)""")
        result = await result.fetchall()
        if result[0][5] == 0:
            print("Fixing primary keys in the database: DO NOT EXIT THE PROGRAM")
            await self.db_conn.execute(create_fixed_history)
            await self.db_conn.commit()

            await self.db_conn.execute("""INSERT INTO media_copy SELECT * FROM media GROUP BY domain, url_path, original_filename;""")
            await self.db_conn.commit()

            await self.db_conn.execute("""DROP TABLE media""")
            await self.db_conn.commit()

            await self.db_conn.execute("""ALTER TABLE media_copy RENAME TO media""")
            await self.db_conn.commit()
