import os
from dataclasses import field, Field
from pathlib import Path

import platformdirs

if os.getenv("PYCHARM_HOSTED") is not None:
    APP_STORAGE = Path("../Test-AppData-Dir")
    DOWNLOAD_STORAGE = Path("../Test-Download-Dir")
else:
    APP_STORAGE = Path("./Test-AppData-Dir")
    DOWNLOAD_STORAGE = Path("./Test-Download-Dir")

# if os.getenv("PYCHARM_HOSTED") is not None:
#     """This is for testing purposes only"""
#     APP_STORAGE = Path("../Test-AppData-Dir")
#     DOWNLOAD_STORAGE = Path("../Test-Download-Dir")
# else:
#     APP_STORAGE: Path = Path(platformdirs.user_config_dir("Cyberdrop-DL"))
#     DOWNLOAD_STORAGE = Path(platformdirs.user_downloads_path())


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
