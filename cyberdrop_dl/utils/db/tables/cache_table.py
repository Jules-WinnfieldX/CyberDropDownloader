from typing import TYPE_CHECKING, Optional

import aiosqlite

from cyberdrop_dl.utils.db.table_definitions import create_cache

if TYPE_CHECKING:
    from yarl import URL


class CacheTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn
        self.ignore_cache: bool = False

    async def startup(self) -> None:
        """Startup process for the CacheTable"""
        await self.db_conn.execute(create_cache)
        await self.db_conn.commit()

    async def insert_blob(self, blob: str, url: 'URL') -> None:
        """Inserts the post content into coomeno"""
        await self.db_conn.execute("""INSERT OR IGNORE INTO cache VALUES (?, ?)""", (url.path, blob,))
        await self.db_conn.commit()

    async def get_blob(self, url: 'URL') -> Optional[str]:
        """returns the post content for a given coomeno post url"""
        if self.ignore_cache:
            return None

        cursor = await self.db_conn.cursor()
        await cursor.execute("""SELECT post_data FROM cache WHERE url_path = ?""", (url.path,))
        sql_file_check = await cursor.fetchone()
        if sql_file_check:
            return sql_file_check[0]
        return None
