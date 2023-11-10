import sqlite3
from pathlib import Path

from cyberdrop_dl.utils.db.table_definitions import create_history, create_temp


def transfer_v4_db(db_path: Path, new_db_path: Path) -> None:
    """Transfers a V4 database into V5 possession"""
    old_db_connection = sqlite3.connect(db_path)
    new_db_connection = sqlite3.connect(new_db_path)

    new_db_connection.execute(create_history)
    new_db_connection.execute(create_temp)

    query = "SELECT domain, url_path, referer, download_filename, original_filename, completed FROM media WHERE completed = 1"
    old_data_history = old_db_connection.execute(query).fetchall()

    new_db_connection.execute("insert into media values (?, ?, ?, ?, ?, ?)", old_data_history)
    del old_data_history

    old_data_temp = old_db_connection.execute("SELECT * FROM temp").fetchall()
    new_db_connection.execute("insert into temp values (?)", old_data_temp)
    del old_data_temp

    new_db_connection.commit()
    old_db_connection.close()
    new_db_connection.close()
