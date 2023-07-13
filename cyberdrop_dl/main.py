import argparse
import asyncio
import atexit
import contextlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import aiofiles
import aiorun
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import (
    CacheManager,
    ErrorFileWriter,
    clear,
    log,
    purge_dir,
)
from cyberdrop_dl.base_functions.config_manager import document_args, run_args
from cyberdrop_dl.base_functions.config_schema import config_default
from cyberdrop_dl.base_functions.sorting_functions import Sorter
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.client.client import Client, ScrapeSession
from cyberdrop_dl.downloader.downloader_utils import check_free_space
from cyberdrop_dl.downloader.downloaders import DownloadDirector
from cyberdrop_dl.downloader.old_downloaders import old_download_forums
from cyberdrop_dl.scraper.Scraper import ScrapeMapper

from .__init__ import __version__ as VERSION
from .base_functions.base_functions import MAX_NAME_LENGTHS
from .base_functions.data_classes import ForumItem, SkipData


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments passed into the program"""
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {VERSION}")

    config_data = config_default["Configuration"]

    # Path options
    config_group = config_data["Files"]
    path_opts = parser.add_argument_group("Path options")
    path_opts.add_argument("-i", "--input-file", type=Path, help="file containing links to download (default: %(default)s)", default=config_group["input_file"])
    path_opts.add_argument("-o", "--output-folder", type=Path, help="folder to download files to (default: %(default)s)", default=config_group["output_folder"])

    path_opts.add_argument("--config-file", type=Path, help="config file to read arguments from (default: %(default)s)", default="config.yaml")
    path_opts.add_argument("--variable-cache-file", type=Path, help="internal variable cache file to read from and write to (default: %(default)s)", default=config_group["variable_cache_file"])
    path_opts.add_argument("--db-file", type=Path, help="history database file to write to (default: %(default)s)", default=config_group["db_file"])
    path_opts.add_argument("--errored-download-urls-file", type=Path, default=config_group["errored_download_urls_file"], help="csv file to write failed download information to (default: %(default)s)")
    path_opts.add_argument("--errored-scrape-urls-file", type=Path, default=config_group["errored_scrape_urls_file"], help="csv file to write failed scrape information to (default: %(default)s)")
    path_opts.add_argument("--log-file", type=Path, help="log file to write to (default: %(default)s)", default=config_group["log_file"])
    path_opts.add_argument("--output-last-forum-post-file", type=Path, default=config_group["output_last_forum_post_file"], help="the text file to output last scraped post from a forum thread for re-feeding into CDL (default: %(default)s)")
    path_opts.add_argument("--unsupported-urls-file", type=Path, default=config_group["unsupported_urls_file"], help="the csv file to output unsupported links into (default: %(default)s)")

    # Ignore
    config_group = config_data["Ignore"]
    ignore_opts = parser.add_argument_group("Ignore options")
    ignore_opts.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    ignore_opts.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    ignore_opts.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    ignore_opts.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    ignore_opts.add_argument("--ignore-cache", help="ignores previous runs cached scrape history", action="store_true")
    ignore_opts.add_argument("--ignore-history", help="ignores previous download history", action="store_true")
    ignore_opts.add_argument("--ignore-input-file", help="ignores the input file and scrapes the input url instead", action="store_true")
    ignore_opts.add_argument("--skip-coomer-ads", help="skips downloading of model advertisements on other models pages", action="store_true")
    ignore_opts.add_argument("--skip-hosts", choices=SkipData.supported_hosts, action="append", help="removes host links from downloads", default=config_group["skip_hosts"])
    ignore_opts.add_argument("--only-hosts", choices=SkipData.supported_hosts, action="append", help="only allows downloads from these hosts", default=config_group["only_hosts"])

    # Runtime arguments
    config_group = config_data["Runtime"]
    runtime_opts = parser.add_argument_group("Runtime options")
    runtime_opts.add_argument("--allow-insecure-connections", help="allows insecure connections from content hosts", action="store_true")
    runtime_opts.add_argument("--attempts", type=int, help="number of attempts to download each file (default: %(default)s)", default=config_group["attempts"])
    runtime_opts.add_argument("--block-sub-folders", help="block sub folders from being created", action="store_true")
    runtime_opts.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    runtime_opts.add_argument("--filesize-maximum-images", type=int, default=config_group["filesize_maximum_images"], help="maximum filesize for images (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--filesize-maximum-videos", type=int, default=config_group["filesize_maximum_videos"], help="maximum filesize for videos (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--filesize-maximum-other", type=int, default=config_group["filesize_maximum_other"], help="maximum filesize for other files (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--filesize-minimum-images", type=int, default=config_group["filesize_minimum_images"], help="minimum filesize for images (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--filesize-minimum-videos", type=int, default=config_group["filesize_minimum_videos"], help="minimum filesize for videos (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--filesize-minimum-other", type=int, default=config_group["filesize_minimum_other"], help="minimum filesize for other files (in bytes) (default: %(default)s)")
    runtime_opts.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    runtime_opts.add_argument("--max-concurrent-threads", type=int, default=config_group["max_concurrent_threads"], help="Number of threads to download simultaneously (default: %(default)s)")
    runtime_opts.add_argument("--max-concurrent-domains", type=int, default=config_group["max_concurrent_domains"], help="Number of domains to download simultaneously (default: %(default)s)")
    runtime_opts.add_argument("--max-concurrent-albums", type=int, default=config_group["max_concurrent_albums"], help="Number of albums to download simultaneously (default: %(default)s)")
    runtime_opts.add_argument("--max-concurrent-downloads-per-domain", type=int, default=config_group["max_concurrent_downloads_per_domain"], help="Number of simultaneous downloads per domain (default: %(default)s)")
    runtime_opts.add_argument("--max-filename-length", type=int, default=config_group["max_filename_length"], help="maximum filename length (default: %(default)s)")
    runtime_opts.add_argument("--max-folder-name-length", type=int, default=config_group["max_folder_name_length"], help="maximum folder name length (default: %(default)s)")
    runtime_opts.add_argument("--skip-check-for-partial-files-and-empty-dirs", help="skip checks for partial files and empty directories after completing", action="store_true")
    runtime_opts.add_argument("--skip-download-mark-completed", help="sets the scraped files as downloaded without downloading", action="store_true")
    runtime_opts.add_argument("--output-errored-urls", help="sets the failed urls to be output to the errored urls file", action="store_true")
    runtime_opts.add_argument("--output-unsupported-urls", help="sets the unsupported urls to be output to the unsupported urls file", action="store_true")
    runtime_opts.add_argument("--proxy", help="HTTP/HTTPS proxy used for downloading, format [protocol]://[ip]:[port]", default=config_group["proxy"])
    runtime_opts.add_argument("--remove-bunkr-identifier", help="removes the bunkr added identifier from output filenames", action="store_true")
    runtime_opts.add_argument("--required-free-space", type=int, default=config_group["required_free_space"], help="required free space (in gigabytes) for the program to run (default: %(default)s)")

    # Sorting
    config_group = config_data["Sorting"]
    sort_opts = parser.add_argument_group("Sorting options")
    sort_opts.add_argument("--sort-downloads", help="sorts downloaded files after downloads have finished", action="store_true")
    sort_opts.add_argument("--sort-directory", type=Path, help="folder to download files to (default: %(default)s)", default=config_group["sort_directory"])
    sort_opts.add_argument("--sorted-audio", help="schema to sort audio (default: %(default)s)", default=config_group["sorted_audio"])
    sort_opts.add_argument("--sorted-images", help="schema to sort images (default: %(default)s)", default=config_group["sorted_images"])
    sort_opts.add_argument("--sorted-others", help="schema to sort other (default: %(default)s)", default=config_group["sorted_others"])
    sort_opts.add_argument("--sorted-videos", help="schema to sort videos (default: %(default)s)", default=config_group["sorted_videos"])

    # Ratelimiting
    config_group = config_data["Ratelimiting"]
    ratelimit_opts = parser.add_argument_group("Ratelimiting options")
    ratelimit_opts.add_argument("--connection-timeout", type=int, default=config_group["connection_timeout"], help="number of seconds to wait attempting to connect to a URL during the downloading phase (default: %(default)s)")
    ratelimit_opts.add_argument("--read-timeout", type=int, default=config_group["read_timeout"], help="number of seconds to wait attempting to read all file data during the downloading phase (default: %(default)s)")
    ratelimit_opts.add_argument("--ratelimit", type=int, default=config_group["ratelimit"], help="this applies to requests made in the program during scraping, the number you provide is in requests/seconds (default: %(default)s)")
    ratelimit_opts.add_argument("--throttle", type=int, default=config_group["throttle"], help="this is a throttle between requests during the downloading phase, the number is in seconds (default: %(default)s)")

    # Forum Options
    forum_opts = parser.add_argument_group("Forum options")
    forum_opts.add_argument("--output-last-forum-post", help="outputs the last post of a forum scrape to use as a starting point for future runs", action="store_true")
    forum_opts.add_argument("--separate-posts", help="separates forum scraping into folders by post number", action="store_true")
    forum_opts.add_argument("--scrape-single-post", help="Scrapes only a single post from the given forum links", action="store_true")

    # Authentication details
    config_group = config_data["Authentication"]
    auth_opts = parser.add_argument_group("Authentication options")
    auth_opts.add_argument("--gofile-api-key", help="api key for premium gofile", default=config_group["gofile_api_key"])
    auth_opts.add_argument("--gofile-website-token", help="website token for gofile", default=config_group["gofile_website_token"])
    auth_opts.add_argument("--imgur-client-id", help="client id for imgur (https://api.imgur.com/oauth2/addclient)", default=config_group["imgur_client_id"])
    auth_opts.add_argument("--pixeldrain-api-key", help="api key for premium pixeldrain", default=config_group["pixeldrain_api_key"])
    auth_opts.add_argument("--reddit-personal-use-script", help="personal use script for reddit (https://www.reddit.com/prefs/apps)", default=config_group["reddit_personal_use_script"])
    auth_opts.add_argument("--reddit-secret", help="secret key for reddit (https://www.reddit.com/prefs/apps)", default=config_group["reddit_secret"])
    auth_opts.add_argument("--nudostar-username", help="username to login to nudostar", default=config_group["nudostar_username"])
    auth_opts.add_argument("--nudostar-password", help="password to login to nudostar", default=config_group['nudostar_password'])
    auth_opts.add_argument("--simpcity-username", help="username to login to simpcity", default=config_group["simpcity_username"])
    auth_opts.add_argument("--simpcity-password", help="password to login to simpcity", default=config_group['simpcity_password'])
    auth_opts.add_argument("--socialmediagirls-username", help="username to login to socialmediagirls", default=config_group["socialmediagirls_username"])
    auth_opts.add_argument("--socialmediagirls-password", help="password to login to socialmediagirls", default=config_group["socialmediagirls_password"])
    auth_opts.add_argument("--xbunker-username", help="username to login to xbunker", default=config_group["xbunker_username"])
    auth_opts.add_argument("--xbunker-password", help="password to login to xbunker", default=config_group["xbunker_password"])

    # JDownloader details
    config_group = config_data["JDownloader"]
    jdownloader_opts = parser.add_argument_group("JDownloader options")
    jdownloader_opts.add_argument("--apply-jdownloader", help="enables sending unsupported URLs to a running jdownloader2 instance to download", action="store_true")
    jdownloader_opts.add_argument("--jdownloader-username", help="username to login to jdownloader", default=config_group["jdownloader_username"])
    jdownloader_opts.add_argument("--jdownloader-password", help="password to login to jdownloader", default=config_group["jdownloader_password"])
    jdownloader_opts.add_argument("--jdownloader-device", help="device name to login to for jdownloader", default=config_group["jdownloader_device"])

    # Progress Options
    config_group = config_data["Progress_Options"]
    progress_opts = parser.add_argument_group("Progress options")
    progress_opts.add_argument("--hide-new-progress", help="disables the new rich progress entirely and uses older methods", action="store_true")
    progress_opts.add_argument("--hide-overall-progress", help="removes overall progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-forum-progress", help="removes forum progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-thread-progress", help="removes thread progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-domain-progress", help="removes domain progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-album-progress", help="removes album progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-file-progress", help="removes file progress section while downloading", action="store_true")
    progress_opts.add_argument("--refresh-rate", type=int, help="refresh rate for the progress table (default: %(default)s)", default=config_group["refresh_rate"])
    progress_opts.add_argument("--visible-rows-threads", type=int, help="number of visible rows to use for the threads table (default: %(default)s)", default=config_group["visible_rows_threads"])
    progress_opts.add_argument("--visible-rows-domains", type=int, help="number of visible rows to use for the domains table (default: %(default)s)", default=config_group["visible_rows_domains"])
    progress_opts.add_argument("--visible-rows-albums", type=int, help="number of visible rows to use for the albums table (default: %(default)s)", default=config_group["visible_rows_albums"])
    progress_opts.add_argument("--visible-rows-files", type=int, help="number of visiblerows to use for the files table (default: %(default)s)", default=config_group["visible_rows_files"])

    # Links
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    return parser.parse_args()


async def file_management(args: Dict, links: List) -> Tuple[ErrorFileWriter, CacheManager]:
    """We handle file defaults here (resetting and creation)"""
    input_file = args['Files']['input_file']
    if not input_file.is_file() and not links:
        input_file.touch()

    Path(args['Files']['output_folder']).mkdir(parents=True, exist_ok=True)

    error_writer = ErrorFileWriter(args['Runtime']['output_errored_urls'], args['Runtime']['output_unsupported_urls'],
                                   args['Forum_Options']['output_last_forum_post'], args['Files']['errored_scrape_urls_file'],
                                   args['Files']['errored_download_urls_file'], args['Files']['unsupported_urls_file'],
                                   args['Files']['output_last_forum_post_file'])

    if args['Forum_Options']['output_last_forum_post']:
        output_url_file = args['Files']['output_last_forum_post_file']
        if output_url_file.exists():
            output_url_file.unlink()
        output_url_file.touch()

    if args['Runtime']['output_unsupported_urls']:
        unsupported_urls = args['Files']['unsupported_urls_file']
        if unsupported_urls.exists():
            unsupported_urls.unlink()
        unsupported_urls.touch()
        await error_writer.write_unsupported_header()

    if args['Runtime']['output_errored_urls']:
        errored_urls = args['Files']['errored_download_urls_file']
        if errored_urls.exists():
            errored_urls.unlink()
        errored_urls.touch()
        await error_writer.write_errored_download_header()

        errored_urls = args['Files']['errored_scrape_urls_file']
        if errored_urls.exists():
            errored_urls.unlink()
        errored_urls.touch()
        await error_writer.write_errored_scrape_header()

    cache_manager = CacheManager(args['Files']['variable_cache_file'])
    await cache_manager.load()

    return error_writer, cache_manager


async def regex_links(urls: List) -> List:
    """Regex grab the links from the URLs.txt file"""
    """This allows code blocks or full paragraphs to be copy and pasted into the URLs.txt"""
    yarl_links = []
    for line in urls:
        if line.lstrip().startswith('#'):
            continue

        all_links = [x.group().replace(".md.", ".") for x in re.finditer(
            r"(?:http.*?)(?=($|\n|\r\n|\r|\s|\"|\[/URL]|]\[|\[/img]))", line)]
        for link in all_links:
            yarl_links.append(URL(link))
    return yarl_links


async def consolidate_links(args: Dict, links: List) -> List:
    """We consolidate links from command line and from URLs.txt into a singular list"""
    links = list(map(URL, links))
    if args["Files"]["input_file"].is_file():
        async with aiofiles.open(args["Files"]["input_file"], "r", encoding="utf8") as f:
            links += await regex_links([line.rstrip() async for line in f])
    links = list(filter(None, links))

    if not links:
        log("No valid links found.", style="red")
    return links


async def scrape_links(scraper: ScrapeMapper, links: List, quiet=False) -> ForumItem:
    """Maps links from URLs.txt or command to the scraper class"""
    log("Starting Scrape", quiet=quiet, style="green")
    tasks = []

    for link in links:
        tasks.append(asyncio.create_task(scraper.map_url(link)))
    await asyncio.wait(tasks)

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    Forums = scraper.Forums
    await Forums.dedupe()

    if not await Cascade.is_empty():
        await Forums.add_thread("Loose Files/Albums", Cascade)

    log("", quiet=quiet)
    log("Finished Scrape", quiet=quiet, style="green")
    return Forums


async def check_outdated(client: Client):
    session = ScrapeSession(client)
    url = URL('https://pypi.python.org/pypi/cyberdrop-dl/json')
    with contextlib.suppress(Exception):
        response = await session.get_json(url)
        if response['info']['version'] != VERSION:
            log(f"\nYour version of Cyberdrop Downloader is outdated. \nYou are running version {VERSION}."
                f"\nPlease update to version {response['info']['version']}"
                f"\nYou can find out how to do that here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/wiki/Frequently-Asked-Questions#how-to-update", style="red")


async def director(args: Dict, links: List) -> None:
    """This is the overarching director coordinator for CDL."""
    await clear()
    await document_args(args)
    log(f"We are running version {VERSION} of Cyberdrop Downloader")
    error_writer, cache_manager = await file_management(args, links)

    MAX_NAME_LENGTHS["FILE"] = args["Runtime"]["max_filename_length"]
    MAX_NAME_LENGTHS["FOLDER"] = args["Runtime"]["max_folder_name_length"]

    if not await check_free_space(args['Runtime']['required_free_space'], args['Files']['output_folder']):
        log("Not enough free space to continue. You can change the required space required using --required-free-space.", style="red")
        exit(1)

    links = await consolidate_links(args, links)
    client = Client(args['Ratelimiting']['ratelimit'], args['Ratelimiting']['throttle'],
                    args['Runtime']['allow_insecure_connections'], args["Ratelimiting"]["connection_timeout"],
                    args["Ratelimiting"]["read_timeout"], args['Runtime']['user_agent'])
    SQL_Helper = SQLHelper(args['Ignore']['ignore_history'], args['Ignore']['ignore_cache'], args['Files']['db_file'])
    Scraper = ScrapeMapper(args, client, SQL_Helper, False, error_writer, cache_manager)

    await SQL_Helper.sql_initialize()

    if links:
        Forums = await scrape_links(Scraper, links)
        await asyncio.sleep(5)
        await clear()

        if not await Forums.is_empty():
            if args['Progress_Options']['hide_new_progress']:
                await old_download_forums(args, Forums, SQL_Helper, client, error_writer)
            else:
                download_director = DownloadDirector(args, Forums, SQL_Helper, client, error_writer)
                await download_director.start()

    if args['Files']['output_folder'].is_dir():
        if args['Sorting']['sort_downloads']:
            log("")
            log("Sorting Downloads")
            sorter = Sorter(args['Files']['output_folder'], args['Sorting']['sort_directory'],
                            args['Sorting']['sorted_audio'], args['Sorting']['sorted_images'],
                            args['Sorting']['sorted_videos'], args['Sorting']['sorted_others'])
            await sorter.sort()

        log("")
        if not args['Runtime']['skip_check_for_partial_files_and_empty_dirs']:
            log("Checking for incomplete downloads")
            partial_downloads = any(f.is_file() for f in args['Files']['output_folder'].rglob("*.part"))
            temp_downloads = any(Path(f).is_file() for f in await SQL_Helper.get_temp_names())

            log('Purging empty directories')
            await purge_dir(args['Files']['output_folder'])
            if partial_downloads:
                log('There are partial downloads in the downloads folder.', style="yellow")
            if temp_downloads:
                log('There are partial downloads from this run, please re-run the program.', style="yellow")

        log('Finished downloading. Enjoy :)')

    await check_outdated(client)
    log("\nIf you enjoy using this program, please consider buying the developer a coffee :)"
        "\nhttps://www.buymeacoffee.com/juleswinnft", style="green")

    with contextlib.suppress(RuntimeError):
        asyncio.get_event_loop().stop()


def main(args=None):
    if not args:
        args = parse_args()

    atexit.register(lambda: print("\x1b[?25h"))

    links = args.links
    args = run_args(args.config_file, argparse.Namespace(**vars(args)).__dict__)

    logging.basicConfig(
        filename=args["Files"]["log_file"],
        level=logging.DEBUG,
        format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
        filemode="w"
    )

    with contextlib.suppress(RuntimeError, asyncio.CancelledError):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        aiorun.run(director(args, links))
        exit(0)


if __name__ == '__main__':
    print("""STOP! If you're just trying to download files, check the README.md file for instructions.
    If you're developing this project, use start.py instead.""")
    exit()
