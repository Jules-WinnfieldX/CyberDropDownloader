import copy
import json
from dataclasses import field
from pathlib import Path

from cyberdrop_dl.managers.args_manager import ArgsManager
from cyberdrop_dl.managers.client_manager import ClientManager
from cyberdrop_dl.managers.db_manager import DBManager
from cyberdrop_dl.managers.cache_manager import CacheManager
from cyberdrop_dl.managers.config_manager import ConfigManager
from cyberdrop_dl.managers.download_manager import DownloadManager
from cyberdrop_dl.managers.log_manager import LogManager
from cyberdrop_dl.managers.path_manager import PathManager
from cyberdrop_dl.managers.progress_manager import ProgressManager
from cyberdrop_dl.managers.queue_manager import QueueManager
from cyberdrop_dl.utils.args import config_definitions
from cyberdrop_dl.utils.dataclasses.supported_domains import SupportedDomains
from cyberdrop_dl.utils.utilities import log


class Manager:
    def __init__(self):
        self.args_manager: ArgsManager = ArgsManager()
        self.cache_manager: CacheManager = CacheManager()
        self.path_manager: PathManager = field(init=False)
        self.config_manager: ConfigManager = field(init=False)
        self.log_manager: LogManager = field(init=False)
        self.queue_manager: QueueManager = QueueManager(self)
        self.db_manager: DBManager = field(init=False)
        self.client_manager: ClientManager = field(init=False)
        self.download_manager: DownloadManager = field(init=False)
        self.progress_manager: ProgressManager = field(init=False)

        self._loaded_args_config: bool = False
        self._made_portable: bool = False

    def startup(self) -> None:
        """Startup process for the manager"""
        self.args_startup()

        self.path_manager = PathManager(self)
        self.path_manager.pre_startup()

        self.cache_manager.startup(self.path_manager.cache_dir / "cache.yaml")
        self.config_manager = ConfigManager(self)
        self.config_manager.startup()

        self.path_manager.startup()
        self.log_manager = LogManager(self)
        self.log_manager.startup()

    def args_startup(self) -> None:
        """Start the args manager"""
        if not self.args_manager.parsed_args:
            self.args_manager.startup()

        if self.args_manager.portable and not self._made_portable:
            self.make_portable()
            self._made_portable = True

    def make_portable(self) -> None:
        """Makes the program portable"""
        from cyberdrop_dl.managers import path_manager
        path_manager.APP_STORAGE = Path.cwd() / "AppData"
        path_manager.DOWNLOAD_STORAGE = Path.cwd() / "Downloads"

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def async_startup(self) -> None:
        """Async startup process for the manager"""
        await self.args_consolidation()
        await self.args_logging()

        self.db_manager = DBManager(self, self.path_manager.history_db)
        self.client_manager = ClientManager(self)
        self.download_manager = DownloadManager(self)
        self.progress_manager = ProgressManager(self)

        from cyberdrop_dl.utils.utilities import MAX_NAME_LENGTHS
        MAX_NAME_LENGTHS['FILE'] = self.config_manager.global_settings_data['General']['max_file_name_length']
        MAX_NAME_LENGTHS['FOLDER'] = self.config_manager.global_settings_data['General']['max_folder_name_length']

        self.db_manager.ignore_history = self.config_manager.settings_data['Runtime_Options']['ignore_history']
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

    async def args_logging(self) -> None:
        """Logs the runtime arguments"""
        forum_xf_cookies_provided = {}
        forum_credentials_provided = {}

        for forum in SupportedDomains.supported_forums_map.values():
            if self.config_manager.authentication_data["Forums"][f"{forum}_xf_user_cookie"]:
                forum_xf_cookies_provided[f"{forum} XF Cookie Provided"] = True
            else:
                forum_xf_cookies_provided[f"{forum} XF Cookie Provided"] = False

            if self.config_manager.authentication_data["Forums"][f"{forum}_username"] and self.config_manager.authentication_data["Forums"][f"{forum}_password"]:
                forum_credentials_provided[f"{forum} Credentials Provided"] = True
            else:
                forum_credentials_provided[f"{forum} Credentials Provided"] = False

        gofile_credentials_provided = True if self.config_manager.authentication_data["GoFile"]['gofile_api_key'] else False
        bunkr_ddg_credentials_provided = False
        coomer_ddg_credentials_provided = False
        kemono_ddg_credentials_provided = False

        if self.config_manager.authentication_data["DDOS-Guard"]['bunkrr_ddg1'] and self.config_manager.authentication_data["DDOS-Guard"]['bunkrr_ddg2'] and self.config_manager.authentication_data["DDOS-Guard"]['bunkrr_ddgid']:
            bunkr_ddg_credentials_provided = True
        if self.config_manager.authentication_data["DDOS-Guard"]['coomer_ddg1']:
            coomer_ddg_credentials_provided = True
        if self.config_manager.authentication_data["DDOS-Guard"]['kemono_ddg1']:
            kemono_ddg_credentials_provided = True

        imgur_credentials_provided = True if self.config_manager.authentication_data["Imgur"]['imgur_client_id'] else False
        jdownloader_credentials_provided = False

        if self.config_manager.authentication_data["JDownloader"]['jdownloader_username'] and self.config_manager.authentication_data["JDownloader"]['jdownloader_password'] and self.config_manager.authentication_data["JDownloader"]['jdownloader_device']:
            jdownloader_credentials_provided = True

        pixeldrain_credentials_provided = True if self.config_manager.authentication_data["PixelDrain"]['pixeldrain_api_key'] else False
        reddit_credentials_provided = False

        if self.config_manager.authentication_data["Reddit"]['reddit_personal_use_script'] and self.config_manager.authentication_data["Reddit"]['reddit_secret']:
            reddit_credentials_provided = True

        auth_provided = {
            "Forums Credentials": forum_credentials_provided,
            "Forums XF Cookies": forum_xf_cookies_provided,
            "GoFile Provided": gofile_credentials_provided,
            "DDOS-Guard": {
                "Bunkrr Provided": bunkr_ddg_credentials_provided,
                "Coomer Provided": coomer_ddg_credentials_provided,
                "Kemono Provided": kemono_ddg_credentials_provided
            },
            "Imgur Provided": imgur_credentials_provided,
            "JDownloader Provided": jdownloader_credentials_provided,
            "PixelDrain Provided": pixeldrain_credentials_provided,
            "Reddit Provided": reddit_credentials_provided
        }

        print_settings = copy.deepcopy(self.config_manager.settings_data)
        print_settings['Files']['input_file'] = str(print_settings['Files']['input_file'])
        print_settings['Files']['download_folder'] = str(print_settings['Files']['download_folder'])
        print_settings["Logs"]["log_folder"] = str(print_settings["Logs"]["log_folder"])
        print_settings['Sorting']['sort_folder'] = str(print_settings['Sorting']['sort_folder'])

        await log(f"Starting Cyberdrop-DL Process for {self.config_manager.loaded_config} Config")
        await log(f"Using Authentication: \n{json.dumps(auth_provided, indent=4, sort_keys=True)}")
        await log(f"Using Settings: \n{json.dumps(print_settings, indent=4, sort_keys=True)}")
        await log(f"Using Global Settings: \n{json.dumps(self.config_manager.global_settings_data, indent=4, sort_keys=True)}")

    async def close(self) -> None:
        """Closes the manager"""
        await self.db_manager.close()
        await self.download_manager.close()
