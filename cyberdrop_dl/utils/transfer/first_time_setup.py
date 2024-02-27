from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import platformdirs
import yaml

from cyberdrop_dl.managers.path_manager import APP_STORAGE, DOWNLOAD_STORAGE
from cyberdrop_dl.utils.transfer.transfer_v4_db import transfer_v4_db

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class TransitionManager:
    def __init__(self, manager: Manager):
        self.manager = manager

    def startup(self) -> None:
        """Startup"""
        OLD_APP_STORAGE: Path = Path(platformdirs.user_config_dir("Cyberdrop-DL"))
        OLD_DOWNLOAD_STORAGE = Path(platformdirs.user_downloads_path()) / "Cyberdrop-DL Downloads"

        if APP_STORAGE.exists():
            cache_file = APP_STORAGE / "Cache" / "cache.yaml"
            if cache_file.is_file() and self.check_cache_for_moved(cache_file):
                return

        OLD_FILES = Path("./Old Files")
        OLD_FILES.mkdir(parents=True, exist_ok=True)

        if OLD_APP_STORAGE.exists():
            if APP_STORAGE.exists():
                if APP_STORAGE.with_name("AppData_OLD").exists():
                    APP_STORAGE.rename(APP_STORAGE.with_name("AppData_OLD2"))
                APP_STORAGE.rename(APP_STORAGE.with_name("AppData_OLD"))
            shutil.copytree(OLD_APP_STORAGE, APP_STORAGE, dirs_exist_ok=True)
            shutil.rmtree(OLD_APP_STORAGE)

        if OLD_DOWNLOAD_STORAGE.exists():
            shutil.copytree(OLD_DOWNLOAD_STORAGE, DOWNLOAD_STORAGE, dirs_exist_ok=True)
            shutil.rmtree(OLD_DOWNLOAD_STORAGE)

        if Path("./download_history.sqlite").is_file():
            transfer_v4_db(Path("./download_history.sqlite"), APP_STORAGE / "Cache" / "cyberdrop.db")
            Path("./download_history.sqlite").rename(OLD_FILES / "download_history1.sqlite")

        if (APP_STORAGE / "download_history.sqlite").is_file():
            transfer_v4_db(APP_STORAGE / "download_history.sqlite", APP_STORAGE / "Cache" / "cyberdrop.db")
            (APP_STORAGE / "download_history.sqlite").rename(OLD_FILES / "download_history2.sqlite")

        if Path("./config.yaml").is_file():
            try:
                self.transfer_v4_config(Path("./config.yaml"), "Imported V4")
                self.update_default_config(APP_STORAGE / "Cache" / "cache.yaml", "Imported V4")
            except Exception:
                pass
            Path("./config.yaml").rename(OLD_FILES / "config.yaml")

        if Path("./downloader.log").is_file():
            Path("./downloader.log").rename(OLD_FILES / "downloader.log")
        if Path("./Errored_Download_URLs.csv").is_file():
            Path("./Errored_Download_URLs.csv").rename(OLD_FILES / "Errored_Download_URLs.csv")
        if Path("./Errored_Scrape_URLs.csv").is_file():
            Path("./Errored_Scrape_URLs.csv").rename(OLD_FILES / "Errored_Scrape_URLs.csv")
        if Path("./Unsupported_URLs.csv").is_file():
            Path("./Unsupported_URLs.csv").rename(OLD_FILES / "Unsupported_URLs.csv")

        self.update_cache(APP_STORAGE / "Cache" / "cache.yaml")
        pass

    def check_cache_for_moved(self, cache_file: Path) -> bool:
        """Checks the cache for moved files"""
        with open(cache_file, 'r') as yaml_file:
            cache = yaml.load(yaml_file.read(), Loader=yaml.FullLoader)
        if cache is None:
            with open(cache_file, 'w') as yaml_file:
                cache = {"first_startup_completed": False}
                yaml.dump(cache, yaml_file)
        moved = bool(cache.get("first_startup_completed", False))
        return moved

    def update_cache(self, cache_file: Path) -> None:
        """Updates the cache to reflect the new location"""
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.touch(exist_ok=True)
        with open(cache_file, 'r') as yaml_file:
            cache = yaml.load(yaml_file.read(), Loader=yaml.FullLoader)
        if cache is None:
            cache = {"first_startup_completed": False}
        cache['first_startup_completed'] = True
        with open(cache_file, 'w') as yaml_file:
            yaml.dump(cache, yaml_file)

    def update_default_config(self, cache_file: Path, config_name: str) -> None:
        """Updates the default config in the cache"""
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.touch(exist_ok=True)
        with open(cache_file, 'r') as yaml_file:
            cache = yaml.load(yaml_file.read(), Loader=yaml.FullLoader)
        if cache is None:
            cache = {"first_startup_completed": False}
        cache['default_config'] = config_name
        with open(cache_file, 'w') as yaml_file:
            yaml.dump(cache, yaml_file)

    def transfer_v4_config(self, old_config_path: Path, new_config_name: str) -> None:
        """Transfers a V4 config into V5 possession"""
        from cyberdrop_dl.utils.args.config_definitions import settings, authentication_settings, global_settings
        new_auth_data = copy.deepcopy(authentication_settings)
        new_user_data = copy.deepcopy(settings)
        new_global_settings_data = copy.deepcopy(global_settings)

        if Path("./URLs.txt").is_file():
            new_user_data['Files']['input_file'] = Path("./URLs.txt")
        else:
            new_user_data['Files']['input_file'] = APP_STORAGE / "Configs" / new_config_name / "URLs.txt"
        new_user_data['Files']['download_folder'] = DOWNLOAD_STORAGE
        new_user_data["Logs"]["log_folder"] = APP_STORAGE / "Configs" / new_config_name / "Logs"
        new_user_data['Sorting']['sort_folder'] = DOWNLOAD_STORAGE / "Cyberdrop-DL Sorted Downloads"

        with open(old_config_path, 'r') as yaml_file:
            old_data = yaml.load(yaml_file.read(), Loader=yaml.FullLoader)
        old_data = old_data['Configuration']

        # Auth data transfer
        new_auth_data['Forums']['nudostar_username'] = old_data['Authentication']['nudostar_username']
        new_auth_data['Forums']['nudostar_password'] = old_data['Authentication']['nudostar_password']
        new_auth_data['Forums']['simpcity_username'] = old_data['Authentication']['simpcity_username']
        new_auth_data['Forums']['simpcity_password'] = old_data['Authentication']['simpcity_password']
        new_auth_data['Forums']['socialmediagirls_username'] = old_data['Authentication']['socialmediagirls_username']
        new_auth_data['Forums']['socialmediagirls_password'] = old_data['Authentication']['socialmediagirls_password']
        new_auth_data['Forums']['xbunker_username'] = old_data['Authentication']['xbunker_username']
        new_auth_data['Forums']['xbunker_password'] = old_data['Authentication']['xbunker_password']

        new_auth_data['JDownloader']['jdownloader_username'] = old_data['JDownloader']['jdownloader_username']
        new_auth_data['JDownloader']['jdownloader_password'] = old_data['JDownloader']['jdownloader_password']
        new_auth_data['JDownloader']['jdownloader_device'] = old_data['JDownloader']['jdownloader_device']

        new_auth_data['Reddit']['reddit_personal_use_script'] = old_data['Authentication']['reddit_personal_use_script']
        new_auth_data['Reddit']['reddit_secret'] = old_data['Authentication']['reddit_secret']

        new_auth_data['GoFile']['gofile_api_key'] = old_data['Authentication']['gofile_api_key']
        new_auth_data['Imgur']['imgur_client_id'] = old_data['Authentication']['imgur_client_id']
        new_auth_data['PixelDrain']['pixeldrain_api_key'] = old_data['Authentication']['pixeldrain_api_key']

        # User data transfer
        new_user_data['Download_Options']['block_download_sub_folders'] = old_data['Runtime']['block_sub_folders']
        new_user_data['Download_Options']['disable_download_attempt_limit'] = old_data['Runtime']['disable_attempt_limit']
        new_user_data['Download_Options']['include_album_id_in_folder_name'] = old_data['Runtime']['include_id']
        new_user_data['Download_Options']['remove_generated_id_from_filenames'] = old_data['Runtime']['remove_bunkr_identifier']
        new_user_data['Download_Options']['separate_posts'] = old_data['Forum_Options']['separate_posts']
        new_user_data['Download_Options']['skip_download_mark_completed'] = False

        new_user_data['File_Size_Limits']['maximum_image_size'] = old_data['Runtime']['filesize_maximum_images']
        new_user_data['File_Size_Limits']['maximum_other_size'] = old_data['Runtime']['filesize_maximum_other']
        new_user_data['File_Size_Limits']['maximum_video_size'] = old_data['Runtime']['filesize_maximum_videos']
        new_user_data['File_Size_Limits']['minimum_image_size'] = old_data['Runtime']['filesize_minimum_images']
        new_user_data['File_Size_Limits']['minimum_other_size'] = old_data['Runtime']['filesize_minimum_other']
        new_user_data['File_Size_Limits']['minimum_video_size'] = old_data['Runtime']['filesize_minimum_videos']

        new_user_data['Ignore_Options']['exclude_videos'] = old_data['Ignore']['exclude_videos']
        new_user_data['Ignore_Options']['exclude_images'] = old_data['Ignore']['exclude_images']
        new_user_data['Ignore_Options']['exclude_other'] = old_data['Ignore']['exclude_other']
        new_user_data['Ignore_Options']['exclude_audio'] = old_data['Ignore']['exclude_audio']
        new_user_data['Ignore_Options']['ignore_coomer_ads'] = old_data['Ignore']['skip_coomer_ads']
        new_user_data['Ignore_Options']['skip_hosts'] = old_data['Ignore']['skip_hosts']
        new_user_data['Ignore_Options']['only_hosts'] = old_data['Ignore']['only_hosts']

        new_user_data['Runtime_Options']['ignore_history'] = old_data['Ignore']['ignore_history']
        new_user_data['Runtime_Options']['skip_check_for_partial_files'] = old_data['Runtime']['skip_check_for_partial_files_and_empty_dirs']
        new_user_data['Runtime_Options']['skip_check_for_empty_folders'] = old_data['Runtime']['skip_check_for_partial_files_and_empty_dirs']
        new_user_data['Runtime_Options']['send_unsupported_to_jdownloader'] = old_data['JDownloader']['apply_jdownloader']

        new_user_data['Sorting']['sort_downloads'] = old_data['Sorting']['sort_downloads']

        if Path("./URLs.txt").is_file():
            new_user_data['Files']['input_file'] = "./URLs.txt"

        # Global data transfer
        new_global_settings_data['General']['allow_insecure_connections'] = old_data['Runtime']['allow_insecure_connections']
        new_global_settings_data['General']['user_agent'] = old_data['Runtime']['user_agent']
        new_global_settings_data['General']['proxy'] = old_data['Runtime']['proxy']
        new_global_settings_data['General']['max_file_name_length'] = old_data['Runtime']['max_filename_length']
        new_global_settings_data['General']['max_folder_name_length'] = old_data['Runtime']['max_folder_name_length']
        new_global_settings_data['General']['required_free_space'] = old_data['Runtime']['required_free_space']

        new_global_settings_data['Rate_Limiting_Options']['connection_timeout'] = old_data['Ratelimiting']['connection_timeout']
        new_global_settings_data['Rate_Limiting_Options']['download_attempts'] = old_data['Runtime']['attempts']
        new_global_settings_data['Rate_Limiting_Options']['download_delay'] = old_data['Ratelimiting']['throttle']
        new_global_settings_data['Rate_Limiting_Options']['read_timeout'] = old_data['Ratelimiting']['read_timeout']
        new_global_settings_data['Rate_Limiting_Options']['rate_limit'] = old_data['Ratelimiting']['ratelimit']
        new_global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'] = old_data['Runtime']['max_concurrent_downloads_per_domain']

        new_user_data['Files']['input_file'] = str(new_user_data['Files']['input_file'])
        new_user_data['Files']['download_folder'] = str(new_user_data['Files']['download_folder'])
        new_user_data["Logs"]["log_folder"] = str(new_user_data["Logs"]["log_folder"])
        new_user_data['Sorting']['sort_folder'] = str(new_user_data['Sorting']['sort_folder'])

        # Write config
        new_config_path = APP_STORAGE / "Configs" / new_config_name / "settings.yaml"
        new_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(new_config_path, 'w') as yaml_file:
            yaml.dump(new_user_data, yaml_file)
        new_auth_path = APP_STORAGE / "Configs" / "authentication.yaml"
        with open(new_auth_path, 'w') as yaml_file:
            yaml.dump(new_auth_data, yaml_file)
        new_global_settings_path = APP_STORAGE / "Configs" / "global_settings.yaml"
        with open(new_global_settings_path, 'w') as yaml_file:
            yaml.dump(new_global_settings_data, yaml_file)
