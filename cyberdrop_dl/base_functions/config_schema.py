config_default = [
    {
        "Configuration": {
            "Apply_Config": False,
            "Files": {
                "input_file": "URLs.txt",
                "output_folder": "Downloads",
                "output_last_forum_post_file": "URLs_last_post.txt",
                "db_file": "download_history.sqlite",
            },
            "Authentication": {
                "simpcity_username": "",
                "simpcity_password": "",
                "socialmediagirls_username": "",
                "socialmediagirls_password": "",
                "xbunker_username": "",
                "xbunker_password": "",
            },
            "JDownloader": {
                "jdownloader_enable": False,
                "jdownloader_username": "",
                "jdownloader_password": "",
                "jdownloader_device": "",
            },
            "Runtime": {
                "threads": 0,
                "attempts": 10,
                "disable_attempt_limit": False,
                "connection_timeout": 15,
                "ratelimit": 50,
                "throttle": 0.5,
                "include_id": False,
                "exclude_videos": False,
                "exclude_images": False,
                "exclude_audio": False,
                "exclude_other": False,
                "ignore_history": False,
                "output_last_forum_post": False,
                "separate_posts": False,
                "mark_downloaded": False,
                "proxy": "",
                "skip_hosts": [],
            }
        }
    }
]

files_args = ["input_file", "output_folder", "output_last_forum_post_file", "db_file"]
authentication_args = ["simpcity_username", "simpcity_password",
                       "socialmediagirls_username", "socialmediagirls_password",
                       "xbunker_username", "xbunker_password"]
jdownloader_args = ["jdownloader_enable", "jdownloader_username", "jdownloader_password", "jdownloader_device"]
runtime_args = ["threads", "attempts", "disable_attempt_limit", "connection_timeout", "ratelimit", "throttle",
                "include_id", "exclude_videos", "exclude_images", "exclude_audio", "exclude_other", "ignore_history",
                "output_last_forum_post", "mark_downloaded", "separate_posts", "skip_hosts", "proxy"]
