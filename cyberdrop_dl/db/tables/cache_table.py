import aiosqlite

from cyberdrop_dl.db.table_definitions import create_cache


class CacheTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn

    async def startup(self) -> None:
        """Startup process for the CacheTable"""
        await self.db_conn.execute(create_cache)
        await self.db_conn.commit()
