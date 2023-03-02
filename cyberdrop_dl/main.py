import argparse
import asyncio
import logging
from pathlib import Path

import aiofiles
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log, clear, regex_links, check_free_space, purge_dir
from cyberdrop_dl.base_functions.config_manager import run_args, document_args
from cyberdrop_dl.base_functions.sorting_functions import Sorter
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.client.client import Client
from cyberdrop_dl.downloader.downloaders import download_cascade, download_forums
from cyberdrop_dl.downloader.old_downloaders import old_download_cascade, old_download_forums
from cyberdrop_dl.scraper.Scraper import ScrapeMapper
from . import __version__ as VERSION
from .base_functions.data_classes import SkipData, CascadeItem


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments passed into the program"""
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)

    # Path options
    parser.add_argument("-i", "--input-file", type=Path, help="file containing links to download", default="URLs.txt")
    parser.add_argument("-o", "--output-folder", type=Path, help="folder to download files to", default="Downloads")

    parser.add_argument("--config-file", type=Path, help="config file to read arguments from", default="config.yaml")
    parser.add_argument("--db-file", type=Path, help="history database file to write to", default="download_history.sqlite")
    parser.add_argument("--errored-urls-file", type=Path, help="csv file to write failed download information to", default="Errored_URLs.csv")
    parser.add_argument("--log-file", type=Path, help="log file to write to", default="downloader.log")
    parser.add_argument("--output-last-forum-post-file", type=Path, help="the text file to output last scraped post from a forum thread for re-feeding into CDL", default="URLs_Last_Post.txt")
    parser.add_argument("--unsupported-urls-file", type=Path, help="the csv file to output unsupported links into", default="Unsupported_URLs.csv")

    # Ignore
    parser.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    parser.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    parser.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    parser.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    parser.add_argument("--ignore-cache", help="ignores previous runs cached scrape history", action="store_true")
    parser.add_argument("--ignore-history", help="ignores previous download history", action="store_true")
    parser.add_argument("--skip-hosts", choices=SkipData.supported_hosts, help="removes host links from downloads", action="append", default=[])

    # Runtime arguments
    parser.add_argument("--allow-insecure-connections", help="allows insecure connections from content hosts", action="store_true")
    parser.add_argument("--attempts", type=int, help="number of attempts to download each file", default=10)
    parser.add_argument("--block-sub-folders", help="block sub folders from being created", action="store_true")
    parser.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    parser.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    parser.add_argument("--skip-download-mark-completed", help="sets the scraped files as downloaded without downloading", action="store_true")
    parser.add_argument("--output-errored-urls", help="sets the failed urls to be output to the errored urls file", action="store_true")
    parser.add_argument("--output-unsupported-urls", help="sets the unsupported urls to be output to the unsupported urls file", action="store_true")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy used for downloading, format [protocal]://[ip]:[port]", default=None)
    parser.add_argument("--remove-bunkr-identifier", help="removes the bunkr added identifier from output filenames", action="store_true")
    parser.add_argument("--required-free-space", type=int, help="required free space (in gigabytes) for the program to run", default=5)
    parser.add_argument("--simultaneous-downloads-per-domain", type=int, help="Number of simultaneous downloads to use per domain", default=4)

    # Sorting
    parser.add_argument("--sort-downloads", help="sorts downloaded files after downloads have finished", action="store_true")
    parser.add_argument("--sort-directory", type=Path, help="folder to download files to", default="Sorted Downloads")
    parser.add_argument("--sorted-audio", type=str, help="schema to sort audio", default="{sort_dir}/{base_dir}/Audio")
    parser.add_argument("--sorted-images", type=str, help="schema to sort images", default="{sort_dir}/{base_dir}/Images")
    parser.add_argument("--sorted-others", type=str, help="schema to sort other", default="{sort_dir}/{base_dir}/Other")
    parser.add_argument("--sorted-videos", type=str, help="schema to sort videos", default="{sort_dir}/{base_dir}/Videos")

    # Ratelimiting
    parser.add_argument("--connection-timeout", type=int, help="number of seconds to wait attempting to connect to a URL during the downloading phase", default=15)
    parser.add_argument("--ratelimit", type=int, help="this applies to requests made in the program during scraping, the number you provide is in requests/seconds", default=50)
    parser.add_argument("--throttle", type=int, help="this is a throttle between requests during the downloading phase, the number is in seconds", default=0.5)

    # Forum Options
    parser.add_argument("--output-last-forum-post", help="outputs the last post of a forum scrape to use as a starting point for future runs", action="store_true")
    parser.add_argument("--separate-posts", help="separates forum scraping into folders by post number", action="store_true")

    # Authentication details
    parser.add_argument("--pixeldrain-api-key", type=str, help="api key for premium pixeldrain", default=None)
    parser.add_argument("--simpcity-password", type=str, help="password to login to simpcity", default=None)
    parser.add_argument("--simpcity-username", type=str, help="username to login to simpcity", default=None)
    parser.add_argument("--socialmediagirls-password", type=str, help="password to login to socialmediagirls", default=None)
    parser.add_argument("--socialmediagirls-username", type=str, help="username to login to socialmediagirls", default=None)
    parser.add_argument("--xbunker-password", type=str, help="password to login to xbunker", default=None)
    parser.add_argument("--xbunker-username", type=str, help="username to login to xbunker", default=None)

    # JDownloader details
    parser.add_argument("--apply-jdownloader", help="enables sending unsupported URLs to a running jdownloader2 instance to download", action="store_true")
    parser.add_argument("--jdownloader-username", type=str, help="username to login to jdownloader", default=None)
    parser.add_argument("--jdownloader-password", type=str, help="password to login to jdownloader", default=None)
    parser.add_argument("--jdownloader-device", type=str, help="device name to login to for jdownloader", default=None)

    # Progress Options
    parser.add_argument("--hide-new-progress", help="disables the new rich progress entirely and uses older methods", action="store_true")
    parser.add_argument("--dont-show-overall-progress", help="removes overall progress section while downloading", action="store_true")
    parser.add_argument("--dont-show-forum-progress", help="removes forum progress section while downloading", action="store_true")
    parser.add_argument("--dont-show-thread-progress", help="removes thread progress section while downloading", action="store_true")
    parser.add_argument("--dont-show-domain-progress", help="removes domain progress section while downloading", action="store_true")
    parser.add_argument("--dont-show-album-progress", help="removes album progress section while downloading", action="store_true")
    parser.add_argument("--dont-show-file-progress", help="removes file progress section while downloading", action="store_true")
    parser.add_argument("--refresh-rate", type=int, help="refresh rate for the progress table", default=10)

    # Links
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    args = parser.parse_args()
    return args


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


async def consolidate_links(args: dict, links: list) -> list:
    """We consolidate links from command line and from URLs.txt into a singular list"""
    links = list(map(URL, links))
    if args["Files"]["input_file"].is_file():
        with open(args["Files"]["input_file"], "r", encoding="utf8") as f:
            links += await regex_links([line.rstrip() for line in f])
    links = list(filter(None, links))

    if not links:
        await log("[red]No valid links found.[/red]")
        exit(1)
    return links


async def scrape_links(scraper: ScrapeMapper, links: list, quiet=False) -> CascadeItem:
    """Maps links from URLs.txt or command to the scraper class"""
    await log("[green]Starting Scrape[/green]", quiet=quiet)
    tasks = []

    for link in links:
        tasks.append(asyncio.create_task(scraper.map_url(link)))
    await asyncio.wait(tasks)

    Cascade = scraper.Cascade
    await Cascade.dedupe()
    Forums = scraper.Forums
    await Forums.dedupe()

    await log("[green]Finished Scrape[/green]", quiet=quiet)
    return Cascade, Forums


async def director(args: dict, links: list) -> None:
    """This is the overarching director coordinator for CDL."""
    await clear()
    await document_args(args)
    await file_management(args, links)
    await log(f"We are running version {VERSION} of Cyberdrop Downloader")

    if not await check_free_space(args['Runtime']['required_free_space'], args['Files']['output_folder']):
        await log("[red]Not enough free space to continue. You can change the required space required using --required-free-space.[/red]")
        exit(1)

    links = await consolidate_links(args, links)
    client = Client(args['Ratelimiting']['ratelimit'], args['Ratelimiting']['throttle'],
                    args['Runtime']['allow_insecure_connections'], args["Ratelimiting"]["connection_timeout"])
    SQL_Helper = SQLHelper(args['Ignore']['ignore_history'], args['Ignore']['ignore_cache'], args['Files']['db_file'])
    Scraper = ScrapeMapper(args, client, SQL_Helper, False)

    await SQL_Helper.sql_initialize()
    Cascade, Forums = await scrape_links(Scraper, links)
    await asyncio.sleep(5)
    await clear()

    if args['Progress_Options']['hide_new_progress']:
        if not await Cascade.is_empty():
            await old_download_cascade(args, Cascade, SQL_Helper, client, Scraper)
        if not await Forums.is_empty():
            await old_download_forums(args, Forums, SQL_Helper, client, Scraper)
    else:
        if not await Cascade.is_empty():
            await download_cascade(args, Cascade, SQL_Helper, client, Scraper)
        if not await Forums.is_empty():
            await download_forums(args, Forums, SQL_Helper, client, Scraper)

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
            await log('[yellow]There are partial downloads in the downloads folder.[/yellow]')
        if temp_downloads_check:
            await log('[yellow]There are partial downloads from this run, please re-run the program.[/yellow]')

    await log('')
    await log("[green]If you enjoy using this program, please consider buying the developer a coffee :)\nhttps://www.buymeacoffee.com/juleswinnft")


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
