from __future__ import annotations

from typing import Dict

from cyberdrop_dl.managers.directory_manager import APP_STORAGE, DOWNLOAD_STORAGE


authentication_settings: Dict = {
    "Forums": {
        "nudostar_xf_user_cookie": "",
        "nudostar_username": "",
        "nudostar_password": "",
        "simpcity_xf_user_cookie": "",
        "simpcity_username": "",
        "simpcity_password": "",
        "socialmediagirls_xf_user_cookie": "",
        "socialmediagirls_username": "",
        "socialmediagirls_password": "",
        "xbunker_xf_user_cookie": "",
        "xbunker_username": "",
        "xbunker_password": "",
    },
    "GoFile": {
        "gofile_api_key": "",
    },
    "Imgur": {
        "imgur_client_id": "",
    },
    "JDownloader": {
        "jdownloader_username": "",
        "jdownloader_password": "",
        "jdownloader_device": "",
    },
    "PixelDrain": {
        "pixeldrain_api_key": "",
    },
    "Reddit": {
        "reddit_personal_use_script": "",
        "reddit_secret": "",
    }
}


settings: Dict = {
    "Download_Options": {
        "block_download_sub_folders": False,
        "disable_download_attempt_limit": False,
        "disable_file_timestamps": False,
        "include_album_id_in_folder_name": False,
        "remove_generated_id_from_filenames": False,
        "skip_download_mark_completed": False,
    },
    "Files": {
        "input_file": str(APP_STORAGE / "Configs" / "Default" / "URLs.txt"),
        "input_password_file": str(APP_STORAGE / "Configs" / "Default" / "URLs & Passwords.txt"),
        "download_folder": str(DOWNLOAD_STORAGE / "Cyberdrop-DL Downloads"),
    },
    "Logs": {
        "log_folder": str(APP_STORAGE / "Configs" / "Default" / "Logs"),
        "main_log_filename": "downloader.log",
        "last_forum_post_filename": "last_scraped_forum_posts.txt",
        "unsupported_urls_filename": "Unsupported_URLs.csv",
        "download_error_urls_filename": "Download_Error_URLs.csv",
        "scrape_error_urls_filename": "Scrape_Error_URLs.csv",
    },
    "File_Size_Limits": {
        "maximum_image_size": 0,
        "maximum_other_size": 0,
        "maximum_video_size": 0,
        "minimum_image_size": 0,
        "minimum_other_size": 0,
        "minimum_video_size": 0,
    },
    "Ignore_Options": {
        "exclude_videos": False,
        "exclude_images": False,
        "exclude_audio": False,
        "exclude_other": False,
        "ignore_coomer_ads": False,
        "skip_hosts": [],
        "only_hosts": [],
    },
    "Runtime_Options": {
        "ignore_cache": False,
        "ignore_history": False,
        "skip_check_for_partial_files": False,
        "skip_check_for_empty_folders": False,
        "delete_partial_files": False,
        "send_unsupported_to_jdownloader": False,
    },
    "Sorting": {
        "sort_downloads": False,
        "sort_folder": str(DOWNLOAD_STORAGE / "Cyberdrop-DL Sorted Downloads"),
        "sorted_audio_folder": "{sort_dir}/{base_dir}/Audio",
        "sorted_image_folder": "{sort_dir}/{base_dir}/Images",
        "sorted_other_folder": "{sort_dir}/{base_dir}/Other",
        "sorted_video_folder": "{sort_dir}/{base_dir}/Videos",
    }
}


global_settings: Dict = {
    "General": {
        "allow_insecure_connections": False,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
        "proxy": "",
        "max_file_name_length": 95,
        "max_folder_name_length": 60,
        "required_free_space": 5,
    },
    "Rate_Limiting_Options": {
        "connection_timeout": 15,
        "download_attempts": 10,
        "read_timeout": 300,
        "rate_limit": 50,
        "download_delay": 0.5,
        "max_simultaneous_downloads": 15,
        "max_simultaneous_downloads_per_domain": 5,
    },
}

