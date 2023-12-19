create_history = """CREATE TABLE IF NOT EXISTS media (domain TEXT,
                                               url_path TEXT,
                                               referer TEXT,
                                               download_path TEXT,
                                               download_filename TEXT,
                                               original_filename TEXT,
                                               completed INTEGER NOT NULL,
                                               PRIMARY KEY (domain, url_path, original_filename)
                                               );"""

create_fixed_history = """CREATE TABLE IF NOT EXISTS media_copy (domain TEXT,
                                               url_path TEXT,
                                               referer TEXT,
                                               download_path TEXT,
                                               download_filename TEXT,
                                               original_filename TEXT,
                                               completed INTEGER NOT NULL,
                                               PRIMARY KEY (domain, url_path, original_filename)
                                               );"""

create_temp = """CREATE TABLE IF NOT EXISTS temp (downloaded_filename TEXT);"""
