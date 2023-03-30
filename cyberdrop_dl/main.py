import argparse
import asyncio
import logging
import re
from pathlib import Path

import aiofiles
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import clear, log, purge_dir
from cyberdrop_dl.base_functions.config_manager import document_args, run_args
from cyberdrop_dl.base_functions.sorting_functions import Sorter
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.client.client import Client
from cyberdrop_dl.downloader.downloader_utils import check_free_space
from cyberdrop_dl.downloader.downloaders import download_cascade, download_forums
from cyberdrop_dl.downloader.old_downloaders import old_download_cascade, old_download_forums
from cyberdrop_dl.scraper.Scraper import ScrapeMapper

from . import __version__ as VERSION
from .base_functions.data_classes import CascadeItem, SkipData


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments passed into the program"""
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {VERSION}")

    # Path options
    path_opts = parser.add_argument_group("Path options")
    path_opts.add_argument("-i", "--input-file", type=Path, help="file containing links to download (default: %(default)s)", default="URLs.txt")
    path_opts.add_argument("-o", "--output-folder", type=Path, help="folder to download files to (default: %(default)s)", default="Downloads")

    path_opts.add_argument("--config-file", type=Path, help="config file to read arguments from (default: %(default)s)", default="config.yaml")
    path_opts.add_argument("--db-file", type=Path, help="history database file to write to (default: %(default)s)", default="download_history.sqlite")
    path_opts.add_argument("--errored-urls-file", type=Path, help="csv file to write failed download information to (default: %(default)s)", default="Errored_URLs.csv")
    path_opts.add_argument("--log-file", type=Path, help="log file to write to (default: %(default)s)", default="downloader.log")
    path_opts.add_argument("--output-last-forum-post-file", type=Path, help="the text file to output last scraped post from a forum thread for re-feeding into CDL (default: %(default)s)", default="URLs_Last_Post.txt")
    path_opts.add_argument("--unsupported-urls-file", type=Path, help="the csv file to output unsupported links into (default: %(default)s)", default="Unsupported_URLs.csv")

    # Ignore
    ignore_opts = parser.add_argument_group("Ignore options")
    ignore_opts.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    ignore_opts.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    ignore_opts.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    ignore_opts.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    ignore_opts.add_argument("--ignore-cache", help="ignores previous runs cached scrape history", action="store_true")
    ignore_opts.add_argument("--ignore-history", help="ignores previous download history", action="store_true")
    ignore_opts.add_argument("--skip-hosts", choices=SkipData.supported_hosts, help="removes host links from downloads", action="append", default=[])
    ignore_opts.add_argument("--only-hosts", choices=SkipData.supported_hosts, help="only allows downloads from these hosts", action="append", default=[])

    # Runtime arguments
    runtime_opts = parser.add_argument_group("Runtime options")
    runtime_opts.add_argument("--allow-insecure-connections", help="allows insecure connections from content hosts", action="store_true")
    runtime_opts.add_argument("--attempts", type=int, help="number of attempts to download each file (default: %(default)s)", default=10)
    runtime_opts.add_argument("--block-sub-folders", help="block sub folders from being created", action="store_true")
    runtime_opts.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    runtime_opts.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    runtime_opts.add_argument("--skip-download-mark-completed", help="sets the scraped files as downloaded without downloading", action="store_true")
    runtime_opts.add_argument("--output-errored-urls", help="sets the failed urls to be output to the errored urls file", action="store_true")
    runtime_opts.add_argument("--output-unsupported-urls", help="sets the unsupported urls to be output to the unsupported urls file", action="store_true")
    runtime_opts.add_argument("--proxy", help="HTTP/HTTPS proxy used for downloading, format [protocal]://[ip]:[port]", default=None)
    runtime_opts.add_argument("--remove-bunkr-identifier", help="removes the bunkr added identifier from output filenames", action="store_true")
    runtime_opts.add_argument("--required-free-space", type=int, help="required free space (in gigabytes) for the program to run (default: %(default)s)", default=5)
    runtime_opts.add_argument("--simultaneous-downloads-per-domain", type=int, help="Number of simultaneous downloads to use per domain (default: %(default)s)", default=4)

    # Sorting
    sort_opts = parser.add_argument_group("Sorting options")
    sort_opts.add_argument("--sort-downloads", help="sorts downloaded files after downloads have finished", action="store_true")
    sort_opts.add_argument("--sort-directory", type=Path, help="folder to download files to (default: %(default)s)", default="Sorted Downloads")
    sort_opts.add_argument("--sorted-audio", type=str, help="schema to sort audio (default: %(default)s)", default="{sort_dir}/{base_dir}/Audio")
    sort_opts.add_argument("--sorted-images", type=str, help="schema to sort images (default: %(default)s)", default="{sort_dir}/{base_dir}/Images")
    sort_opts.add_argument("--sorted-others", type=str, help="schema to sort other (default: %(default)s)", default="{sort_dir}/{base_dir}/Other")
    sort_opts.add_argument("--sorted-videos", type=str, help="schema to sort videos (default: %(default)s)", default="{sort_dir}/{base_dir}/Videos")

    # Ratelimiting
    ratelimit_opts = parser.add_argument_group("Ratelimiting options")
    ratelimit_opts.add_argument("--connection-timeout", type=int, help="number of seconds to wait attempting to connect to a URL during the downloading phase (default: %(default)s)", default=15)
    ratelimit_opts.add_argument("--ratelimit", type=int, help="this applies to requests made in the program during scraping, the number you provide is in requests/seconds (default: %(default)s)", default=50)
    ratelimit_opts.add_argument("--throttle", type=int, help="this is a throttle between requests during the downloading phase, the number is in seconds (default: %(default)s)", default=0.5)

    # Forum Options
    forum_opts = parser.add_argument_group("Forum options")
    forum_opts.add_argument("--output-last-forum-post", help="outputs the last post of a forum scrape to use as a starting point for future runs", action="store_true")
    forum_opts.add_argument("--separate-posts", help="separates forum scraping into folders by post number", action="store_true")

    # Authentication details
    auth_opts = parser.add_argument_group("Authentication options")
    auth_opts.add_argument("--pixeldrain-api-key", type=str, help="api key for premium pixeldrain", default=None)
    auth_opts.add_argument("--simpcity-password", type=str, help="password to login to simpcity", default=None)
    auth_opts.add_argument("--simpcity-username", type=str, help="username to login to simpcity", default=None)
    auth_opts.add_argument("--socialmediagirls-password", type=str, help="password to login to socialmediagirls", default=None)
    auth_opts.add_argument("--socialmediagirls-username", type=str, help="username to login to socialmediagirls", default=None)
    auth_opts.add_argument("--xbunker-password", type=str, help="password to login to xbunker", default=None)
    auth_opts.add_argument("--xbunker-username", type=str, help="username to login to xbunker", default=None)

    # JDownloader details
    jdownloader_opts = parser.add_argument_group("JDownloader options")
    jdownloader_opts.add_argument("--apply-jdownloader", help="enables sending unsupported URLs to a running jdownloader2 instance to download", action="store_true")
    jdownloader_opts.add_argument("--jdownloader-username", type=str, help="username to login to jdownloader", default=None)
    jdownloader_opts.add_argument("--jdownloader-password", type=str, help="password to login to jdownloader", default=None)
    jdownloader_opts.add_argument("--jdownloader-device", type=str, help="device name to login to for jdownloader", default=None)

    # Progress Options
    progress_opts = parser.add_argument_group("Progress options")
    progress_opts.add_argument("--hide-new-progress", help="disables the new rich progress entirely and uses older methods", action="store_true")
    progress_opts.add_argument("--hide-overall-progress", help="removes overall progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-forum-progress", help="removes forum progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-thread-progress", help="removes thread progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-domain-progress", help="removes domain progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-album-progress", help="removes album progress section while downloading", action="store_true")
    progress_opts.add_argument("--hide-file-progress", help="removes file progress section while downloading", action="store_true")
    progress_opts.add_argument("--refresh-rate", type=int, help="refresh rate for the progress table (default: %(default)s)", default=10)

    # Links
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    return parser.parse_args()


async def file_management(args: dict, links: list) -> None:
    """We handle file defaults here (resetting and creation)"""
    input_file = args['Files']['input_file']
    if not input_file.is_file() and not links:
        input_file.touch()

    Path(args['Files']['output_folder']).mkdir(parents=True, exist_ok=True)

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
            async with aiofiles.open(unsupported_urls, mode='w') as f:
                await f.write("URL,REFERER,TITLE\n")

    if args['Runtime']['output_errored_urls']:
        errored_urls = args['Files']['errored_urls_file']
        if errored_urls.exists():
            errored_urls.unlink()
            errored_urls.touch()
            async with aiofiles.open(errored_urls, mode='w') as f:
                await f.write("URL,REFERER,REASON\n")


async def regex_links(urls: list) -> list:
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


async def consolidate_links(args: dict, links: list) -> list:
    """We consolidate links from command line and from URLs.txt into a singular list"""
    links = list(map(URL, links))
    if args["Files"]["input_file"].is_file():
        with open(args["Files"]["input_file"], "r", encoding="utf8") as f:
            links += await regex_links([line.rstrip() for line in f])
    links = list(filter(None, links))

    if not links:
        await log("No valid links found.", style="red")
    return links


async def scrape_links(scraper: ScrapeMapper, links: list, quiet=False) -> CascadeItem:
    """Maps links from URLs.txt or command to the scraper class"""
    await log("Starting Scrape", quiet=quiet, style="green")
    tasks = []

    for link in links:
        tasks.append(asyncio.create_task(scraper.map_url(link)))
    await asyncio.wait(tasks)

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    Forums = scraper.Forums
    await Forums.dedupe()

    await log("", quiet=quiet)
    await log("Finished Scrape", quiet=quiet, style="green")
    return Cascade, Forums


async def director(args: dict, links: list) -> None:
    """This is the overarching director coordinator for CDL."""
    await clear()
    await document_args(args)
    await file_management(args, links)
    await log(f"We are running version {VERSION} of Cyberdrop Downloader")

    if not await check_free_space(args['Runtime']['required_free_space'], args['Files']['output_folder']):
        await log("Not enough free space to continue. You can change the required space required using --required-free-space.", style="red")
        exit(1)

    links = await consolidate_links(args, links)
    client = Client(args['Ratelimiting']['ratelimit'], args['Ratelimiting']['throttle'],
                    args['Runtime']['allow_insecure_connections'], args["Ratelimiting"]["connection_timeout"])
    SQL_Helper = SQLHelper(args['Ignore']['ignore_history'], args['Ignore']['ignore_cache'], args['Files']['db_file'])
    Scraper = ScrapeMapper(args, client, SQL_Helper, False)

    await SQL_Helper.sql_initialize()

    if links:
        Cascade, Forums = await scrape_links(Scraper, links)
        await asyncio.sleep(5)
        await clear()

        if args['Progress_Options']['hide_new_progress']:
            if not await Cascade.is_empty():
                await old_download_cascade(args, Cascade, SQL_Helper, client)
            if not await Forums.is_empty():
                await old_download_forums(args, Forums, SQL_Helper, client)
        else:
            if not await Cascade.is_empty():
                await download_cascade(args, Cascade, SQL_Helper, client)
            if not await Forums.is_empty():
                await download_forums(args, Forums, SQL_Helper, client)

    if args['Files']['output_folder'].is_dir():
        if args['Sorting']['sort_downloads']:
            await log("")
            await log("Sorting Downloads")
            sorter = Sorter(args['Files']['output_folder'], args['Sorting']['sort_directory'],
                            args['Sorting']['sorted_audio'], args['Sorting']['sorted_images'],
                            args['Sorting']['sorted_videos'], args['Sorting']['sorted_others'],)
            await sorter.sort()

        await log("")
        await log("Checking for incomplete downloads")
        partial_downloads = [str(f) for f in args['Files']['output_folder'].rglob("*.part") if f.is_file()]
        temp_downloads_check = [str(f) for f in await SQL_Helper.get_temp_names() if Path(f).is_file()]

        await log('Purging empty directories')
        await purge_dir(args['Files']['output_folder'])

        await log('Finished downloading. Enjoy :)')
        if partial_downloads:
            await log('There are partial downloads in the downloads folder.', style="yellow")
        if temp_downloads_check:
            await log('There are partial downloads from this run, please re-run the program.', style="yellow")

    await log('')
    await log("If you enjoy using this program, please consider buying the developer a coffee :)\nhttps://www.buymeacoffee.com/juleswinnft", style="green")


def main(args=None):
    if not args:
        args = parse_args()

    links = args.links
    args = run_args(args.config_file, argparse.Namespace(**vars(args)).__dict__)

    logging.basicConfig(
        filename=args["Files"]["log_file"],
        level=logging.DEBUG,
        format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
        filemode="w"
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(director(args, links))
        loop.run_until_complete(asyncio.sleep(5))
    except RuntimeError:
        pass


if __name__ == '__main__':
    print("""STOP! If you're just trying to download files, check the README.md file for instructions.
    If you're developing this project, use start.py instead.""")
    exit()
