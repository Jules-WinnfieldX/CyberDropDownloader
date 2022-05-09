import atexit
import logging
import sqlite3


class SQLHelper:
    def __init__(self, ignore_history, download_history):
        self.ignore_history = ignore_history
        self.download_history = download_history
        self.conn = None
        self.curs = None
        # Close the sql connection when the program exits
        atexit.register(self.exit_handler)

    async def sql_initialize(self):
        self.conn = sqlite3.connect(self.download_history)
        self.curs = self.conn.cursor()
        create_table_query = """CREATE TABLE IF NOT EXISTS downloads (
                                    filename TEXT,
                                    downloaded_filename TEXT,
                                    size INTEGER NOT NULL,
                                    completed INTEGER NOT NULL,
                                    PRIMARY KEY (filename, size)
                                );"""
        self.curs.execute(create_table_query)
        self.conn.commit()
        await self.check_columns()

    async def check_columns(self):
        self.curs.execute("""SELECT COUNT(*) AS CNTREC FROM pragma_table_info('downloads') WHERE 
                             name='downloaded_filename'""")
        sql_check = self.curs.fetchone()[0]
        if sql_check == (0):
            create_table_query = """CREATE TABLE IF NOT EXISTS downloads_temp (
                                                filename TEXT,
                                                downloaded_filename TEXT,
                                                size INTEGER NOT NULL,
                                                completed INTEGER NOT NULL,
                                                PRIMARY KEY (filename, size)
                                            );"""
            self.curs.execute(create_table_query)
            self.conn.commit()
            self.curs.execute("""INSERT INTO downloads_temp SELECT filename, filename, size, completed from downloads""")
            self.curs.execute("""DROP TABLE downloads""")
            self.curs.execute("""ALTER TABLE downloads_temp RENAME TO downloads""")
            self.conn.commit()

    async def sql_check_existing(self, filename, size):
        if self.ignore_history:
            return False
        self.curs.execute("""SELECT completed FROM downloads WHERE filename = ? and size = ?""", (filename, size))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            if sql_file_check[0] == 1:
                return True
        return False

    async def sql_insert_file(self, filename, downloaded_filename, size, completed):
        self.curs.execute("""INSERT OR IGNORE INTO downloads VALUES (?, ?, ?, ?)""", (filename, downloaded_filename, size, completed))
        self.conn.commit()

    async def sql_update_file(self, filename, downloaded_filename, size, completed):
        self.curs.execute("""INSERT OR REPLACE INTO downloads VALUES (?, ?, ?, ?)""", (filename, downloaded_filename, size, completed))
        self.conn.commit()

    async def check_filename(self, filename):
        self.curs.execute("""SELECT EXISTS(SELECT 1 FROM downloads WHERE filename = ?)""", (filename, ))
        sql_check = self.curs.fetchone()[0]
        if sql_check == 1:
            return True
        else:
            return False

    async def check_filename_for_downloaded(self, filename):
        self.curs.execute("""SELECT EXISTS(SELECT 1 FROM downloads WHERE downloaded_filename = ?)""", (filename, ))
        sql_check = self.curs.fetchone()[0]
        if sql_check == 1:
            return True
        else:
            return False

    async def get_download_filename(self, filename, size):
        self.curs.execute("""SELECT downloaded_filename FROM downloads WHERE filename = ? and size = ?""", (filename, size))
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
