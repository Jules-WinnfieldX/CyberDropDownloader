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
        self.original_filename = original_filename
        self.filesize: int = field(init=False)


class ScrapeItem:
    def __init__(self, url: URL, parent_title: str):
        self.url: URL = url
        self.parent_title: str = parent_title
