import copy
from pathlib import Path
from typing import Dict

import yaml

from cyberdrop_dl.utils.args.config_definitions import settings
from cyberdrop_dl.managers.manager import Manager


def _save_yaml(file: Path, data: Dict) -> None:
    """Saves a dict to a yaml file"""
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, 'w') as yaml_file:
        yaml.dump(data, yaml_file)


def _load_yaml(file: Path) -> Dict:
    """Loads a yaml file and returns it as a dict"""
    with open(file, 'r') as yaml_file:
        return yaml.load(yaml_file.read(), Loader=yaml.FullLoader)


def transfer_v4_config(manager: Manager, old_config_path: Path, new_config_name: str) -> None:
    """Transfers a V4 config into V5 possession"""
    new_auth_data = manager.config_manager.authentication_data
    new_user_data = copy.deepcopy(settings)

    from cyberdrop_dl.managers.path_manager import APP_STORAGE, DOWNLOAD_STORAGE
    new_user_data['Files']['input_file'] = APP_STORAGE / "Configs" / new_config_name / "URLs.txt"
    new_user_data['Files']['download_folder'] = DOWNLOAD_STORAGE / "Cyberdrop-DL Downloads"
    new_user_data["Logs"]["log_folder"] = APP_STORAGE / "Configs" / new_config_name / "Logs"
    new_user_data['Sorting']['sort_folder'] = DOWNLOAD_STORAGE / "Cyberdrop-DL Sorted Downloads"

    new_global_data = manager.config_manager.global_settings_data
    old_data = _load_yaml(old_config_path)
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

    # Global data transfer
    new_global_data['General']['allow_insecure_connections'] = old_data['Runtime']['allow_insecure_connections']
    new_global_data['General']['user_agent'] = old_data['Runtime']['user_agent']
    new_global_data['General']['proxy'] = old_data['Runtime']['proxy']
    new_global_data['General']['max_file_name_length'] = old_data['Runtime']['max_filename_length']
    new_global_data['General']['max_folder_name_length'] = old_data['Runtime']['max_folder_name_length']
    new_global_data['General']['required_free_space'] = old_data['Runtime']['required_free_space']

    new_global_data['Rate_Limiting_Options']['connection_timeout'] = old_data['Ratelimiting']['connection_timeout']
    new_global_data['Rate_Limiting_Options']['download_attempts'] = old_data['Runtime']['attempts']
    new_global_data['Rate_Limiting_Options']['download_delay'] = old_data['Ratelimiting']['throttle']
    new_global_data['Rate_Limiting_Options']['read_timeout'] = old_data['Ratelimiting']['read_timeout']
    new_global_data['Rate_Limiting_Options']['rate_limit'] = old_data['Ratelimiting']['ratelimit']
    new_global_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'] = old_data['Runtime']['max_concurrent_downloads_per_domain']

    # Save Data
    new_settings = manager.path_manager.config_dir / new_config_name / "settings.yaml"
    new_logs = manager.path_manager.config_dir / new_config_name / "Logs"
    new_settings.parent.mkdir(parents=True, exist_ok=True)
    new_logs.mkdir(parents=True, exist_ok=True)

    old_config_path = Path(old_config_path).parent
    old_urls_path = Path(old_data['Files']['input_file'])

    new_urls = manager.path_manager.config_dir / new_config_name / "URLs.txt"
    new_urls.touch(exist_ok=True)

    if old_urls_path.is_absolute():
        with open(str(old_urls_path), 'r') as urls_file:
            urls = urls_file.readlines()
        with open(new_urls, 'w') as urls_file:
            urls_file.writelines(urls)
    elif len(old_urls_path.parts) == 1:
        if (old_config_path / old_urls_path.name).is_file():
            with open(str(old_config_path / old_urls_path.name), 'r') as urls_file:
                urls = urls_file.readlines()
            with open(new_urls, 'w') as urls_file:
                urls_file.writelines(urls)
    else:
        new_urls.touch(exist_ok=True)

    manager.config_manager.create_new_config(new_settings, new_user_data)
    manager.config_manager.write_updated_authentication_config()
    manager.config_manager.write_updated_global_settings_config()
    manager.config_manager.change_config(new_config_name)
