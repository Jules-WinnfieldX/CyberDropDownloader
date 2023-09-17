from dataclasses import field
from pathlib import Path

from cyberdrop_dl.managers.args_manager import ArgsManager
from cyberdrop_dl.managers.client_manager import ClientManager
from cyberdrop_dl.managers.db_manager import DBManager
from cyberdrop_dl.managers.cache_manager import CacheManager
from cyberdrop_dl.managers.config_manager import ConfigManager
from cyberdrop_dl.managers.directory_manager import DirectoryManager
from cyberdrop_dl.managers.download_manager import DownloadManager
from cyberdrop_dl.managers.file_manager import FileManager
from cyberdrop_dl.managers.progress_manager import ProgressManager
from cyberdrop_dl.managers.queue_manager import QueueManager
from cyberdrop_dl.utils.args import config_definitions


def make_portable() -> None:
    """Makes the program portable"""
    from cyberdrop_dl.managers import directory_manager
    directory_manager.APP_STORAGE = Path.cwd() / "AppData"
    directory_manager.DOWNLOAD_STORAGE = Path.cwd() / "Downloads"

    from cyberdrop_dl.utils.args.config_definitions import settings
    settings['Files']['input_file'] = str(directory_manager.APP_STORAGE / "Configs" / "Default" / "URLs.txt")
    settings['Files']['input_password_file'] = str(directory_manager.APP_STORAGE / "Configs" / "Default" / "URLs & Passwords.txt")
    settings['Files']['download_folder'] = str(directory_manager.DOWNLOAD_STORAGE / "Cyberdrop-DL Downloads")

    settings['Logs']['log_folder'] = str(directory_manager.APP_STORAGE / "Configs" / "Default" / "Logs")

    settings['Sorting']['sort_folder'] = str(directory_manager.DOWNLOAD_STORAGE / "Cyberdrop-DL Downloads" / "Sorted")


class Manager:
    def __init__(self):
        self.args_manager: ArgsManager = ArgsManager()
        self.cache_manager: CacheManager = CacheManager()
        self.directory_manager: DirectoryManager = DirectoryManager()
        self.config_manager: ConfigManager = ConfigManager(self)
        self.file_manager: FileManager = FileManager()
        self.queue_manager: QueueManager = QueueManager()
        self.db_manager: DBManager = field(init=False)
        self.client_manager: ClientManager = field(init=False)
        self.download_manager: DownloadManager = field(init=False)
        self.progress_manager: ProgressManager = field(init=False)

        self.cache_manager.startup(self.directory_manager.cache / "cache.yaml")

        self._loaded_args_config: bool = False
        self._made_portable: bool = False

    def startup(self) -> None:
        """Startup process for the manager"""
        self.args_startup()
        self.config_startup()
        self.directory_startup()
        self.file_startup()

    def args_startup(self) -> None:
        """Start the args manager"""
        if not self.args_manager.parsed_args:
            self.args_manager.startup()

        if self.args_manager.portable and not self._made_portable:
            make_portable()

    def config_startup(self) -> None:
        """Start the config manager"""
        if not isinstance(self.config_manager.loaded_config, str):
            self.config_manager.loaded_config = self.cache_manager.get("default_config")
        if self.args_manager.load_config_from_args and not self._loaded_args_config:
            self.config_manager.loaded_config = self.args_manager.load_config_name

        self.config_manager.authentication_settings = self.directory_manager.configs / "authentication_settings.yaml"
        self.config_manager.settings = self.directory_manager.configs / self.config_manager.loaded_config / "settings.yaml"
        self.config_manager.global_settings = self.directory_manager.configs / "global_settings.yaml"

        self.config_manager.startup()

    def directory_startup(self) -> None:
        """Start the directory manager"""
        self.directory_manager.downloads = Path(self.config_manager.settings_data['Files']['download_folder'])
        if self.config_manager.settings_data['Sorting']['sort_downloads']:
            self.directory_manager.sorted_downloads = Path(self.config_manager.settings_data['Sorting']['sort_folder'])
        self.directory_manager.logs = Path(self.config_manager.settings_data['Logs']['log_folder'])

        self.directory_manager.startup()

    def file_startup(self) -> None:
        """Start the file manager"""
        self.file_manager.input_file = Path(self.config_manager.settings_data['Files']['input_file'])
        self.file_manager.input_password_file = Path(self.config_manager.settings_data['Files']['input_password_file'])

        self.file_manager.history_db = Path(self.directory_manager.cache / "cyberdrop.db")

        self.file_manager.main_log = Path(
            self.directory_manager.logs / self.config_manager.settings_data['Logs']['main_log_filename'])
        self.file_manager.last_post_log = Path(
            self.directory_manager.logs / self.config_manager.settings_data['Logs']['last_forum_post_filename'])
        self.file_manager.unsupported_urls_log = Path(
            self.directory_manager.logs / self.config_manager.settings_data['Logs']['unsupported_urls_filename'])
        self.file_manager.download_error_log = Path(
            self.directory_manager.logs / self.config_manager.settings_data['Logs']['download_error_urls_filename'])
        self.file_manager.scrape_error_log = Path(
            self.directory_manager.logs / self.config_manager.settings_data['Logs']['scrape_error_urls_filename'])

        self.file_manager.startup()

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def async_startup(self) -> None:
        """Async startup process for the manager"""
        await self.args_consolidation()

        self.db_manager = DBManager(self.file_manager.history_db)
        self.client_manager = ClientManager(self)
        self.download_manager = DownloadManager(self)
        self.progress_manager = ProgressManager()

        from cyberdrop_dl.utils.utilities import MAX_NAME_LENGTHS
        MAX_NAME_LENGTHS['FILE'] = self.config_manager.global_settings_data['General']['max_file_name_length']
        MAX_NAME_LENGTHS['FOLDER'] = self.config_manager.global_settings_data['General']['max_folder_name_length']

        self.db_manager.ignore_history = self.config_manager.settings_data['Runtime_Options']['ignore_history']
        self.db_manager.ignore_cache = self.config_manager.settings_data['Runtime_Options']['ignore_cache']
        await self.db_manager.startup()
        await self.progress_manager.startup()

    async def args_consolidation(self) -> None:
        """Consolidates runtime arguments with config values"""
        for arg in self.args_manager.parsed_args.keys():
            if arg in config_definitions.settings['Download_Options']:
                if self.args_manager.parsed_args[arg] != config_definitions.settings['Download_Options'][arg]:
                    self.config_manager.settings_data['Download_Options'][arg] = self.args_manager.parsed_args[arg]
            elif arg in config_definitions.settings['File_Size_Limits']:
                if self.args_manager.parsed_args[arg] != config_definitions.settings['File_Size_Limits'][arg]:
                    self.config_manager.settings_data['File_Size_Limits'][arg] = self.args_manager.parsed_args[arg]
            elif arg in config_definitions.settings['Ignore_Options']:
                if self.args_manager.parsed_args[arg] != config_definitions.settings['Ignore_Options'][arg]:
                    self.config_manager.settings_data['Ignore_Options'][arg] = self.args_manager.parsed_args[arg]
            elif arg in config_definitions.settings['Runtime_Options']:
                if self.args_manager.parsed_args[arg] != config_definitions.settings['Runtime_Options'][arg]:
                    self.config_manager.settings_data['Runtime_Options'][arg] = self.args_manager.parsed_args[arg]

    async def close(self) -> None:
        """Closes the manager"""
        await self.db_manager.close()
        await self.download_manager.close()
