import aiosqlite
from yarl import URL

from cyberdrop_dl.utils.db.table_definitions import create_history


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
