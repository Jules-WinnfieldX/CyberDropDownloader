import argparse

from cyberdrop_dl import __version__ as VERSION
from cyberdrop_dl.utils.dataclasses.supported_domains import SupportedDomains


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments passed into the program"""
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    general = parser.add_argument_group("General")
    general.add_argument("-V", "--version", action="version", version=f"%(prog)s {VERSION}")
    general.add_argument("--config", type=str, help="name of config to load", default="")
    general.add_argument("--proxy", type=str, help="manually specify proxy string", default="")
    general.add_argument("--no-ui", action="store_true", help="Disables the UI/Progress view entirely", default=False)
    general.add_argument("--download", action="store_true", help="Skip the UI and go straight to downloading", default=False)
    general.add_argument("--download-all-configs", action="store_true", help="Skip the UI and go straight to downloading (runs all configs sequentially)", default=False)
    general.add_argument("--retry-failed", action="store_true", help="retry failed downloads", default=False)

    # File Paths
    file_paths = parser.add_argument_group("File_Paths")
    file_paths.add_argument("-i", "--input-file", type=str, help="path to txt file containing urls to download", default="")
    file_paths.add_argument("-d", "--output-folder", type=str, help="path to download folder", default="")
    file_paths.add_argument("--config-file", type=str, help="path to the CDL settings.yaml file to load", default="")
    file_paths.add_argument("--appdata-folder", type=str, help="path to where you want CDL to store it's AppData folder", default="")
    file_paths.add_argument("--log-folder", type=str, help="path to where you want CDL to store it's log files", default="")

    # Settings
    download_options = parser.add_argument_group("Download_Options")
    download_options.add_argument("--block-download-sub-folders", action="store_true", help="block sub folder creation", default=False)
    download_options.add_argument("--disable-download-attempt-limit", action="store_true", help="disable download attempt limit", default=False)
    download_options.add_argument("--disable-file-timestamps", action="store_true", help="disable file timestamps", default=False)
    download_options.add_argument("--include-album-id-in-folder-name", action="store_true", help="include album id in folder name", default=False)
    download_options.add_argument("--include-thread-id-in-folder-name", action="store_true", help="include thread id in folder name", default=False)
    download_options.add_argument("--remove-domains-from-folder-names", action="store_true", help="remove website domains from folder names", default=False)
    download_options.add_argument("--remove-generated-id-from-filenames", action="store_true", help="remove site generated id from filenames", default=False)
    download_options.add_argument("--skip-download-mark-completed", action="store_true", help="skip download and mark as completed in history", default=False)

    file_size_limits = parser.add_argument_group("File_Size_Limits")
    file_size_limits.add_argument("--maximum-image-size", type=int, help="maximum image size in bytes (default: %(default)s)", default=0)
    file_size_limits.add_argument("--maximum-video-size", type=int, help="maximum video size in bytes (default: %(default)s)", default=0)
    file_size_limits.add_argument("--maximum-other-size", type=int, help="maximum other size in bytes (default: %(default)s)", default=0)
    file_size_limits.add_argument("--minimum-image-size", type=int, help="minimum image size in bytes (default: %(default)s)", default=0)
    file_size_limits.add_argument("--minimum-video-size", type=int, help="minimum video size in bytes (default: %(default)s)", default=0)
    file_size_limits.add_argument("--minimum-other-size", type=int, help="minimum other size in bytes (default: %(default)s)", default=0)

    ignore_options = parser.add_argument_group("Ignore_Options")
    ignore_options.add_argument("--exclude-videos", action="store_true", help="exclude videos from downloading", default=False)
    ignore_options.add_argument("--exclude-images", action="store_true", help="exclude images from downloading", default=False)
    ignore_options.add_argument("--exclude-audio", action="store_true", help="exclude images from downloading", default=False)
    ignore_options.add_argument("--exclude-other", action="store_true", help="exclude other files from downloading", default=False)
    ignore_options.add_argument("--ignore-coomer-ads", action="store_true", help="ignore coomer ads when scraping", default=False)
    ignore_options.add_argument("--skip-hosts", choices=SupportedDomains.supported_hosts, action="append", help="skip these domains when scraping", default=[])
    ignore_options.add_argument("--only-hosts", choices=SupportedDomains.supported_hosts, action="append", help="only scrape these domains", default=[])

    runtime_options = parser.add_argument_group("Runtime_Options")
    runtime_options.add_argument("--ignore-history", action="store_true", help="ignore history when scraping", default=False)
    runtime_options.add_argument("--log-level", type=int, help="set the log level (default: %(default)s)", default=10)
    runtime_options.add_argument("--skip-check-for-partial-files", action="store_true", help="skip check for partial downloads", default=False)
    runtime_options.add_argument("--skip-check-for-empty-folders", action="store_true", help="skip check (and removal) for empty folders", default=False)
    runtime_options.add_argument("--delete-partial-files", action="store_true", help="delete partial downloads", default=False)
    runtime_options.add_argument("--send-unsupported-to-jdownloader", action="store_true", help="send unsupported urls to jdownloader", default=False)

    # Links
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    return parser.parse_args()
