from dataclasses import field, Field
from pathlib import Path


# APP_STORAGE: Path = Path(platformdirs.user_config_dir("Cyberdrop-DL"))
APP_STORAGE = Path("../Test-AppData-Dir")
# DOWNLOAD_STORAGE = Path(platformdirs.user_downloads_path())
DOWNLOAD_STORAGE = Path("../Test-Download-Dir")


class DirectoryManager:
    def __init__(self):
        self.cache: Path = APP_STORAGE / "Cache"
        self.configs: Path = APP_STORAGE / "Configs"

        self.downloads: Path = field(init=False)
        self.sorted_downloads: Path = field(init=False)
        self.logs: Path = field(init=False)

    def startup(self) -> None:
        """Startup process for the Directory Manager"""
        self.downloads.mkdir(parents=True, exist_ok=True)
        if not isinstance(self.sorted_downloads, Field):
            self.sorted_downloads.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
