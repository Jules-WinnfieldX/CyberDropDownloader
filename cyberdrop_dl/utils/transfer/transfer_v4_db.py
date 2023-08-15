import sqlite3
from pathlib import Path

from cyberdrop_dl.db.table_definitions import create_history, create_cache, create_temp


def transfer_v4_db(db_path: Path, new_db_path: Path) -> None:
    old_db_connection = sqlite3.connect(db_path)
    new_db_connection = sqlite3.connect(new_db_path)

    new_db_connection.execute(create_history)
    new_db_connection.execute(create_cache)
    new_db_connection.execute(create_temp)

    old_data_history = old_db_connection.execute("SELECT * FROM media").fetchall()
    new_db_connection.execute("insert into media values (?, ?, ?, ?, ?, ?, ?, ?)", old_data_history)
    del old_data_history

    old_data_temp = old_db_connection.execute("SELECT * FROM temp").fetchall()
    new_db_connection.execute("insert into temp values (?)", old_data_temp)
    del old_data_temp

    old_data_cache = old_db_connection.execute("SELECT * FROM coomeno").fetchall()
    new_db_connection.execute("insert into cache values (?, ?)", old_data_cache)
    del old_data_cache

    new_db_connection.commit()
    old_db_connection.close()
    new_db_connection.close()

