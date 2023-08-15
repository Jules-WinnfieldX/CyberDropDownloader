import aiosqlite

from cyberdrop_dl.utils.db.table_definitions import create_temp


class TempTable:
    def __init__(self, db_conn: aiosqlite.Connection):
        self.db_conn: aiosqlite.Connection = db_conn

    async def startup(self) -> None:
        """Startup process for the TempTable"""
        await self.db_conn.execute(create_temp)
        await self.db_conn.commit()
