import atexit
import logging
import sqlite3
import os


class SQLHelper:
    def __init__(self, ignore_history, download_history):
        self.ignore_history = ignore_history
        self.download_history = download_history
        self.conn = None
        self.curs = None
        # Close the sql connection when the program exits
        atexit.register(self.exit_handler)

    async def sql_initialize(self):
        if os.path.exists("download_history_size_based.sqlite"):
            os.remove("download_history_size_based.sqlite")
        self.conn = sqlite3.connect(self.download_history)
        self.curs = self.conn.cursor()
        create_table_query = """CREATE TABLE IF NOT EXISTS downloads (
                                    path TEXT,
                                    downloaded_filename TEXT,
                                    completed INTEGER NOT NULL,
                                    PRIMARY KEY (path)
                                );"""
        self.curs.execute(create_table_query)
        self.conn.commit()
        await self.check_columns()

    async def check_columns(self):
        self.curs.execute("""SELECT COUNT(*) AS CNTREC FROM pragma_table_info('downloads') WHERE 
                             name='path'""")
        sql_check = self.curs.fetchone()[0]
        if sql_check == (0):
            self.curs.execute("""DROP TABLE downloads""")
            self.conn.commit()
            create_table_query = """CREATE TABLE IF NOT EXISTS downloads (
                                    path TEXT,
                                    downloaded_filename TEXT,
                                    completed INTEGER NOT NULL,
                                    PRIMARY KEY (path)
                                );"""
            self.curs.execute(create_table_query)
            self.conn.commit()

    async def sql_check_existing(self, path):
        if self.ignore_history:
            return False
        self.curs.execute("""SELECT completed FROM downloads WHERE path = ?""", (path, ))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            if sql_file_check[0] == 1:
                return True
        return False

    async def sql_insert_file(self, path, downloaded_filename, completed):
        self.curs.execute("""INSERT OR IGNORE INTO downloads VALUES (?, ?, ?)""", (path, downloaded_filename, completed, ))
        self.conn.commit()

    async def sql_update_file(self, path, downloaded_filename, completed):
        self.curs.execute("""INSERT OR REPLACE INTO downloads VALUES (?, ?, ?)""", (path, downloaded_filename, completed, ))
        self.conn.commit()

    async def check_filename(self, filename):
        self.curs.execute("""SELECT EXISTS(SELECT 1 FROM downloads WHERE downloaded_filename = ?)""", (filename, ))
        sql_check = self.curs.fetchone()[0]
        if sql_check == 1:
            return True
        else:
            return False

    async def get_download_filename(self, path):
        self.curs.execute("""SELECT downloaded_filename FROM downloads WHERE path = ?""", (path, ))
        filename = self.curs.fetchone()
        if filename:
            return filename[0]
        else:
            return None

    def exit_handler(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            logging.debug(f"Failed to close sqlite database connection: {str(e)}")
        else:
            logging.debug("Successfully closed sqlite database connection")
