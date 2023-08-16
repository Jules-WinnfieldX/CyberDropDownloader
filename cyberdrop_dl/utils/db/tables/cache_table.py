import aiosqlite

from cyberdrop_dl.utils.db.table_definitions import create_cache


class CacheTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn
        self.ignore_cache: bool = False

    async def startup(self) -> None:
        """Startup process for the CacheTable"""
        await self.db_conn.execute(create_cache)
        await self.db_conn.commit()
