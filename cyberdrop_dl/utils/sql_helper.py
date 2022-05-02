import sqlite3
import atexit
import logging


class SQLHelper():
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
                                    size INTEGER NOT NULL,
                                    completed INTEGER NOT NULL,
                                    PRIMARY KEY (filename, size)
                                );"""
        self.curs.execute(create_table_query)
        self.conn.commit()

    async def sql_check_existing(self, filename, size):
        if self.ignore_history:
            return False
        self.curs.execute("""SELECT completed FROM downloads WHERE filename = '%s' and size = %d""" % (filename, size))
        sql_file_check = self.curs.fetchone()
        if sql_file_check:
            if sql_file_check[0] == 1:
                return True
        return False

    async def sql_insert_file(self, filename, size, completed):
        self.curs.execute("""INSERT OR IGNORE INTO downloads VALUES ('%s', %d, %d)""" % (filename, size, completed))
        self.conn.commit()

    async def sql_update_file(self, filename, size, completed):
        self.curs.execute("""INSERT OR REPLACE INTO downloads VALUES ('%s', %d, %d)""" % (filename, size, completed))
        self.conn.commit()

    def exit_handler(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            logging.debug(f"Failed to close sqlite database connection: {str(e)}")
        else:
            logging.debug("Successfully closed sqlite database connection")
        