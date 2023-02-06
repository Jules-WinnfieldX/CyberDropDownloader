import atexit
import logging
import sqlite3
from pathlib import Path

from cyberdrop_dl.base_functions.base_functions import get_db_path
from cyberdrop_dl.base_functions.data_classes import AlbumItem, CascadeItem, MediaItem, DomainItem


class SQLHelper:
    """This class is responsible for handling SQL operations"""
    def __init__(self, ignore_history, ignore_cache, download_history):
        self.ignore_history = ignore_history
        self.ignore_cache = ignore_cache
        self.download_history = download_history
        self.conn = None
        self.curs = None
        # Close the sql connection when the program exits
        atexit.register(self.exit_handler)

    async def sql_initialize(self):
        """Initializes the SQL connection, and makes sure necessary tables exist"""
        self.conn = sqlite3.connect(self.download_history)
        self.curs = self.conn.cursor()

        await self.pre_allocate()
        await self.create_media_history()
        await self.create_coomer_history()

    async def create_media_history(self):
        """We create the download history tables here"""
        create_table_query = """CREATE TABLE IF NOT EXISTS media (
                                                    domain TEXT,
                                                    url_path TEXT,
                                                    album_path TEXT,
                                                    referrer TEXT,
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

    async def create_coomer_history(self):
        create_table_query = """CREATE TABLE IF NOT EXISTS coomer (
                                                            url_path TEXT,
                                                            post_data BLOB,
                                                            PRIMARY KEY (url_path)
                                                        );"""
        self.curs.execute(create_table_query)
        self.conn.commit()

    async def pre_allocate(self):
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

    async def get_temp_names(self):
        self.curs.execute("SELECT downloaded_filename FROM downloads_temp;")
        filenames = self.curs.fetchall()
        filenames = list(sum(filenames, ()))
        return filenames

    async def insert_media(self, domain: str, url_path: str, album_path: str, referrer: str, download_path: str,
                           download_filename: str, original_filename: str, completed: int):
        self.curs.execute("""INSERT OR IGNORE INTO media VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (domain, url_path, album_path, referrer, download_path, download_filename, original_filename, completed,))
        self.conn.commit()

    async def insert_album(self, domain: str, album_path: str, album: AlbumItem):
        if album.media:
            for media in album.media:
                if not media.complete:
                    url_path = await get_db_path(media.url)
                    self.curs.execute("""INSERT OR IGNORE INTO media VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                      (domain, url_path, album_path, str(media.referrer), "", "", media.filename, 0,))
        self.conn.commit()

    async def insert_domain(self, domain_name: str, album_path: str, domain: DomainItem):
        if domain.albums:
            for title, album in domain.albums.items():
                for media in album.media:
                    if not media.complete:
                        url_path = await get_db_path(media.url)
                        self.curs.execute("""INSERT OR IGNORE INTO media VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                          (domain_name, url_path, album_path, str(media.referrer), "", "", media.filename, 0,))
        self.conn.commit()

    async def insert_cascade(self, cascade: CascadeItem):
        if not await cascade.is_empty():
            for domain, domain_obj in cascade.domains.items():
                for title, album_obj in domain_obj.albums.items():
                    for media in album_obj.media:
                        if not media.complete:
                            url_path = media.url.path
                            self.curs.execute("""INSERT OR IGNORE INTO media VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                              (domain, url_path, media.referrer.path, str(media.referrer), "",
                                               "", media.filename, 0,))
        self.conn.commit()

    async def get_downloaded_filename(self, url_path, filename):
        self.curs.execute("""SELECT download_filename FROM media WHERE url_path = ? and original_filename = ?""", (url_path, filename,))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            return sql_file_check[0]
        return None

    async def check_filename(self, filename):
        self.curs.execute("""SELECT EXISTS(SELECT 1 FROM media WHERE download_filename = ?)""", (filename, ))
        sql_check = self.curs.fetchone()[0]
        return sql_check == 1

    async def check_existing(self, domain, url_path):
        if self.ignore_cache:
            return False
        self.curs.execute("""SELECT completed FROM media WHERE domain = ? and url_path = ?""", (domain, url_path,))
        sql_file_check = self.curs.fetchone()
        if not sql_file_check:
            return False
        return True

    async def get_existing(self, domain, url_path):
        self.curs.execute("""SELECT * FROM media WHERE domain = ? and url_path = ?""", (domain, url_path,))
        rows = self.curs.fetchall()
        return rows

    async def get_existing_album(self, domain, album_path):
        self.curs.execute("""SELECT * FROM media WHERE domain = ? and album_path = ?""", (domain, album_path,))
        rows = self.curs.fetchall()
        return rows

    async def check_complete_singular(self, domain, url_path):
        self.curs.execute("""SELECT completed FROM media WHERE domain = ? and url_path = ?""", (domain, url_path,))
        sql_file_check = self.curs.fetchone()
        if not sql_file_check:
            return False
        elif sql_file_check[0] == 0:
            return False
        else:
            return True

    async def update_pre_download(self, path: Path, filename: str, url_path: str, original_filename: str):
        self.curs.execute("""UPDATE media SET download_path = ?, download_filename = ? WHERE url_path = ? AND original_filename = ?""", (str(path), filename, url_path, original_filename,))
        self.conn.commit()

    async def mark_complete(self, url_path: str, original_filename: str):
        self.curs.execute("""UPDATE media SET completed = 1 WHERE url_path = ? AND original_filename = ?""", (url_path, original_filename,))
        self.conn.commit()

    async def sql_insert_temp(self, downloaded_filename):
        self.curs.execute("""INSERT OR IGNORE INTO downloads_temp VALUES (?)""", (downloaded_filename,))
        self.conn.commit()

    def exit_handler(self):
        """Exit handler on unexpected exits"""
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            logging.debug(f"Failed to close sqlite database connection: {str(e)}")
        else:
            logging.debug("Successfully closed sqlite database connection")
