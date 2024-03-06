import sqlite3
from pathlib import Path

from cyberdrop_dl.utils.database.table_definitions import create_history, create_temp


def transfer_v4_db(db_path: Path, new_db_path: Path) -> None:
    """Transfers a V4 database into V5 possession"""
    old_db_connection = sqlite3.connect(db_path)
    if not new_db_path.exists():
        new_db_path.parent.mkdir(parents=True, exist_ok=True)
        new_db_path.touch()
    new_db_connection = sqlite3.connect(new_db_path)

    new_db_connection.execute(create_history)
    new_db_connection.execute(create_temp)

    query = "SELECT domain, url_path, referer, download_path, download_filename, original_filename, completed FROM media WHERE completed = 1"
    old_data_history = old_db_connection.execute(query).fetchall()

    old_data_revised = []
    for row in old_data_history:
        row = list(row)
        row[3] = str(Path(row[3]).parent)
        old_data_revised.append(tuple(row))

    new_db_connection.executemany("insert or ignore into media (domain, url_path, referer, download_path, download_filename, original_filename, completed) values (?, ?, ?, ?, ?, ?, ?)", old_data_revised)
    del old_data_history

    new_db_connection.commit()
    old_db_connection.close()
    new_db_connection.close()
