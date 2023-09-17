from dataclasses import field
from pathlib import Path

from yarl import URL


class MediaItem:
    def __init__(self, url: URL, referer: URL, download_folder: Path, filename: str, ext: str, original_filename: str):
        self.url = url
        self.referer = referer
        self.download_folder: Path = download_folder
        self.filename = filename
        self.ext = ext
        self.download_filename: str = field(init=False)
        self.original_filename = original_filename
        self.filesize: int = field(init=False)
        self.current_attempt: int = field(init=False)


class ScrapeItem:
    def __init__(self, url: URL, parent_title: str, part_of_album: bool = False, password: str = None):
        self.url: URL = url
        self.parent_title: str = parent_title
        self.part_of_album: bool = part_of_album
        self.password: str = field(init=False)
        if password:
            self.password: str = password
