from dataclasses import field
from typing import TYPE_CHECKING

import aiofiles

if TYPE_CHECKING:
    from pathlib import Path
    from yarl import URL


class FileManager:
    def __init__(self):
        self.input_file: Path = field(init=False)
        self.history_db: Path = field(init=False)

        self.main_log: Path = field(init=False)
        self.last_post_log: Path = field(init=False)
        self.unsupported_urls_log: Path = field(init=False)
        self.download_error_log: Path = field(init=False)
        self.scrape_error_log: Path = field(init=False)

    def startup(self) -> None:
        """Startup process for the file manager"""
        self.input_file.touch(exist_ok=True)

        self.main_log.unlink(missing_ok=True)
        self.main_log.touch(exist_ok=True)
        self.last_post_log.unlink(missing_ok=True)
        self.last_post_log.touch(exist_ok=True)
        self.unsupported_urls_log.unlink(missing_ok=True)
        self.unsupported_urls_log.touch(exist_ok=True)
        self.download_error_log.unlink(missing_ok=True)
        self.download_error_log.touch(exist_ok=True)
        self.scrape_error_log.unlink(missing_ok=True)
        self.scrape_error_log.touch(exist_ok=True)

    async def write_last_post_log(self, url: 'URL') -> None:
        """Writes to the last post log"""
        async with aiofiles.open(self.last_post_log, 'a') as f:
            await f.write(f"{url}\n")

    async def write_unsupported_urls_log(self, url: 'URL') -> None:
        """Writes to the unsupported urls log"""
        async with aiofiles.open(self.unsupported_urls_log, 'a') as f:
            await f.write(f"{url}\n")

    async def write_download_error_log(self, url: 'URL', error_message: str) -> None:
        """Writes to the download error log"""
        async with aiofiles.open(self.download_error_log, 'a') as f:
            await f.write(f"{url},{error_message}\n")

    async def write_scrape_error_log(self, url: 'URL', error_message: str) -> None:
        """Writes to the scrape error log"""
        async with aiofiles.open(self.scrape_error_log, 'a') as f:
            await f.write(f"{url},{error_message}\n")
