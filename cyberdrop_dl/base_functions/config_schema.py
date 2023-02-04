config_default = [
    {
        "Configuration": {
            "Apply_Config": False,
            "Files": {
                "db_file": "download_history.sqlite",
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
            "Ratelimiting": {
                "connection_timeout": 15,
                "ratelimit": 50,
                "throttle": 0.5,
            },
            "Runtime": {
                "simultaneous_downloads": 0,
                "allow_insecure_connections": False,
                "attempts": 10,
                "required_free_space": 5,
                "disable_attempt_limit": False,
                "include_id": False,
                "mark_downloaded": False,
                "proxy": "",
            }
        }
    }
]

authentication_args = ["pixeldrain_api_key",
                       "simpcity_username", "simpcity_password",
                       "socialmediagirls_username", "socialmediagirls_password",
                       "xbunker_username", "xbunker_password"]

files_args = ["db_file", "input_file", "log_file", "output_folder", "output_last_forum_post_file", "unsupported_urls_file"]

forum_args = ["output_last_forum_post", "separate_posts"]

ignore_args = ["exclude_videos", "exclude_images", "exclude_audio", "exclude_other", "ignore_cache", "ignore_history",
               "skip_hosts"]

jdownloader_args = ["apply_jdownloader", "jdownloader_username", "jdownloader_password", "jdownloader_device"]

ratelimiting_args = ["connection_timeout", "ratelimit", "throttle"]

runtime_args = ["simultaneous_downloads", "allow_insecure_connections", "attempts", "disable_attempt_limit",
                "include_id",  "mark_downloaded", "proxy", "required_free_space"]
