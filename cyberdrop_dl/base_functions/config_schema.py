config_default = [
    {
        "Configuration": {
            "Apply_Config": False,
            "Files": {
                "db_file": "download_history.sqlite",
                "errored_urls_file": "Errored_URLs.csv",
                "input_file": "URLs.txt",
                "log_file": "downloader.log",
                "output_folder": "Downloads",
                "output_last_forum_post_file": "URLs_last_post.txt",
                "unsupported_urls_file": "Unsupported_URLs.csv",
            },
            "Authentication": {
                "pixeldrain_api_key": "",
                "simpcity_username": "",
                "simpcity_password": "",
                "socialmediagirls_username": "",
                "socialmediagirls_password": "",
                "xbunker_username": "",
                "xbunker_password": "",
            },
            "JDownloader": {
                "apply_jdownloader": False,
                "jdownloader_username": "",
                "jdownloader_password": "",
                "jdownloader_device": "",
            },
            "Forum_Options": {
                "output_last_forum_post": False,
                "separate_posts": False,
            },
            "Ignore": {
                "exclude_videos": False,
                "exclude_images": False,
                "exclude_audio": False,
                "exclude_other": False,
                "ignore_cache": False,
                "ignore_history": False,
                "skip_hosts": [],
            },
            "Progress_Options": {
                "dont_show_overall_progress": False,
                "dont_show_forum_progress": False,
                "dont_show_thread_progress": False,
                "dont_show_domain_progress": False,
                "dont_show_album_progress": False,
                "dont_show_file_progress": False
            },
            "Ratelimiting": {
                "connection_timeout": 15,
                "ratelimit": 50,
                "throttle": 0.5,
            },
            "Runtime": {
                "allow_insecure_connections": False,
                "attempts": 10,
                "block_sub_folders": False,
                "disable_attempt_limit": False,
                "include_id": False,
                "skip_download_mark_completed": False,
                "output_errored_urls": False,
                "output_unsupported_urls": False,
                "proxy": "",
                "remove_bunkr_identifier": False,
                "required_free_space": 5,
                "simultaneous_downloads_per_domain": 4,
            },
            "Sorting": {
                "sort_downloads": False,
                "sort_directory": "Sorted Downloads",
                "sorted_audio": "{sort_dir}/{base_dir}/Audio",
                "sorted_images": "{sort_dir}/{base_dir}/Images",
                "sorted_others": "{sort_dir}/{base_dir}/Other",
                "sorted_videos": "{sort_dir}/{base_dir}/Videos"
            }
        }
    }
]

authentication_args = ["pixeldrain_api_key",
                       "simpcity_username", "simpcity_password",
                       "socialmediagirls_username", "socialmediagirls_password",
                       "xbunker_username", "xbunker_password"]

files_args = ["db_file", "input_file", "log_file", "output_folder", "output_last_forum_post_file",
              "unsupported_urls_file", "errored_urls_file"]

forum_args = ["output_last_forum_post", "separate_posts"]

ignore_args = ["exclude_videos", "exclude_images", "exclude_audio", "exclude_other", "ignore_cache", "ignore_history",
               "skip_hosts"]

jdownloader_args = ["apply_jdownloader", "jdownloader_username", "jdownloader_password", "jdownloader_device"]

progress_args = ["dont_show_overall_progress", "dont_show_forum_progress", "dont_show_thread_progress",
                 "dont_show_domain_progress", "dont_show_album_progress", "dont_show_file_progress"]

ratelimiting_args = ["connection_timeout", "ratelimit", "throttle"]

runtime_args = ["simultaneous_downloads_per_domain", "allow_insecure_connections", "attempts", "disable_attempt_limit",
                "include_id", "skip_download_mark_completed", "proxy", "required_free_space", "output_errored_urls",
                "output_unsupported_urls", "block_sub_folders"]

sorting_args = ["sort_downloads", "sort_directory", "sorted_audio", "sorted_images", "sorted_others", "sorted_videos"]
