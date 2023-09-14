from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class FileManager:
    def __init__(self):
        self.input_file: Path = field(init=False)
        self.input_password_file: Path = field(init=False)

        self.history_db: Path = field(init=False)

        self.main_log: Path = field(init=False)
        self.last_post_log: Path = field(init=False)
        self.unsupported_urls_log: Path = field(init=False)
        self.download_error_log: Path = field(init=False)
        self.scrape_error_log: Path = field(init=False)

    def startup(self) -> None:
        """Startup process for the file manager"""
        self.input_file.touch(exist_ok=True)
        self.input_password_file.touch(exist_ok=True)

        self.main_log.touch(exist_ok=True)
        self.last_post_log.touch(exist_ok=True)
        self.unsupported_urls_log.touch(exist_ok=True)
        self.download_error_log.touch(exist_ok=True)
        self.scrape_error_log.touch(exist_ok=True)
