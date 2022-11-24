import argparse
import multiprocessing
from argparse import Namespace
import asyncio
import logging
from pathlib import Path
from functools import wraps
from typing import Dict

from colorama import Fore
from yarl import URL

from . import __version__ as VERSION
from cyberdrop_dl.base_functions.base_functions import clear, create_config, log, logger, purge_dir, regex_links, \
    run_args
from cyberdrop_dl.base_functions.data_classes import AuthData, SkipData
from cyberdrop_dl.base_functions.sql_helper import SQLHelper
from cyberdrop_dl.client.client import Client
from cyberdrop_dl.client.downloaders import get_downloaders
from cyberdrop_dl.scraper.scraper import scrape


def parse_args():
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("-i", "--input-file", type=Path, help="file containing links to download", default="URLs.txt")
    parser.add_argument("-o", "--output-folder", type=Path, help="folder to download files to", default="Downloads")
    parser.add_argument("--log-file", type=Path, help="log file to write to", default="downloader.log")
    parser.add_argument("--config-file", type=Path, help="config file to read arguments from", default="config.yaml")
    parser.add_argument("--db-file", type=Path, help="history database file to write to", default="download_history.sqlite")
    parser.add_argument("--threads", type=int, help="number of threads to use (0 = max)", default=0)
    parser.add_argument("--attempts", type=int, help="number of attempts to download each file", default=10)
    parser.add_argument("--connection-timeout", type=int, help="number of seconds to wait attempting to connect to a URL during the downloading phase", default=15)
    parser.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    parser.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    parser.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    parser.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    parser.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    parser.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    parser.add_argument("--ignore-history", help="This ignores previous download history", action="store_true")
    parser.add_argument("--output-last-forum-post", help="Separates forum scraping into folders by post number", action="store_true")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy used for downloading, format [protocal]://[ip]:[port]", default=None)
    parser.add_argument("--separate-posts", help="Separates forum scraping into folders by post number", action="store_true")
    parser.add_argument("--mark-downloaded", help="Sets the scraped files as downloaded without downloading", action="store_true")
    parser.add_argument("--xbunker-username", type=str, help="username to login to xbunker", default=None)
    parser.add_argument("--xbunker-password", type=str, help="password to login to xbunker", default=None)
    parser.add_argument("--socialmediagirls-username", type=str, help="username to login to socialmediagirls", default=None)
    parser.add_argument("--socialmediagirls-password", type=str, help="password to login to socialmediagirls", default=None)
    parser.add_argument("--simpcity-username", type=str, help="username to login to simpcity", default=None)
    parser.add_argument("--simpcity-password", type=str, help="password to login to simpcity", default=None)
    parser.add_argument("--jdownloader-enable", help="enables sending unsupported URLs to a running jdownloader2 instance to download", action="store_true")
    parser.add_argument("--jdownloader-username", type=str, help="username to login to jdownloader", default=None)
    parser.add_argument("--jdownloader-password", type=str, help="password to login to jdownloader", default=None)
    parser.add_argument("--jdownloader-device", type=str, help="device name to login to for jdownloader", default=None)
    parser.add_argument("--skip", dest="skip_hosts", choices=SkipData.supported_hosts, help="This removes host links from downloads", action="append", default=[])
    parser.add_argument("--ratelimit", type=int, help="this will add a ratelimiter to requests made in the program during scraping, the number you provide is in requests/seconds", default=50)
    parser.add_argument("--throttle", type=int, help="This is a throttle between requests during the downloading phase, the number is in seconds", default=0.5)
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    args = parser.parse_args()
    return args


async def handle_args(args: argparse.Namespace):
    print_args = Namespace(**vars(args)).__dict__
    print_args['xbunker_password'] = '!REDACTED!'
    print_args['socialmediagirls_password'] = '!REDACTED!'
    print_args['simpcity_password'] = '!REDACTED!'
    print_args['jdownloader_password'] = '!REDACTED!'

    logging.debug("Creating Config")
    cmd_args = Namespace(**vars(args)).__dict__
    await create_config(args.config_file, print_args)

    await log("Getting Run Args")
    use_args = await run_args(args.config_file, cmd_args)

    auth_args = use_args['Authentication']
    auth_args_print = auth_args.copy()
    auth_args_print['xbunker_password'] = '!REDACTED!'
    auth_args_print['socialmediagirls_password'] = '!REDACTED!'
    auth_args_print['simpcity_password'] = '!REDACTED!'

    file_args = use_args['Files']
    for key, value in file_args.items():
        file_args[key] = Path(value)

    jdownloader_args = use_args['JDownloader']
    jdownloader_args_print = jdownloader_args.copy()
    jdownloader_args_print['jdownloader_password'] = '!REDACTED!'

    runtime_args = use_args['Runtime']

    logging.debug(f"Starting Cyberdrop-DL")
    logging.debug(f"Using authorization arguments: {auth_args_print}")
    logging.debug(f"Using file arguments: {file_args}")
    logging.debug(f"Using jdownloader arguments: {jdownloader_args_print}")
    logging.debug(f"Using runtime arguments: {runtime_args}")

    return auth_args, file_args, jdownloader_args, runtime_args


async def download_all(auth_args: Dict, file_args: Dict, jdownloader_args: Dict, runtime_args: Dict, links: list,
                       client: Client, SQL_helper: SQLHelper, threads: int):
    xbunker_auth = AuthData(auth_args['xbunker_username'], auth_args['xbunker_password'])
    socialmediagirls_auth = AuthData(auth_args['socialmediagirls_username'], auth_args['socialmediagirls_password'])
    simpcity_auth = AuthData(auth_args['simpcity_username'], auth_args['simpcity_password'])
    jdownloader_auth = AuthData(jdownloader_args['jdownloader_username'], jdownloader_args['jdownloader_password'])

    skip_data = SkipData(runtime_args['skip_hosts'])
    excludes = {'videos': runtime_args['exclude_videos'], 'images': runtime_args['exclude_images'],
                'audio': runtime_args['exclude_audio'], 'other': runtime_args['exclude_other']}

    content_object = await scrape(urls=links, client=client, file_args=file_args, jdownloader_args=jdownloader_args,
                                  runtime_args=runtime_args, jdownloader_auth=jdownloader_auth,
                                  simpcity_auth=simpcity_auth, socialmediagirls_auth=socialmediagirls_auth,
                                  xbunker_auth=xbunker_auth, skip_data=skip_data, quiet=False)

    if await content_object.is_empty():
        logging.error('ValueError No links')
        await log("No links found duing scraping, check passwords or that the urls are accessible", Fore.RED)
        await log("This program does not currently support password protected albums.", Fore.RED)
        exit(0)
    await clear()

    downloaders = await get_downloaders(content_object, excludes=excludes, SQL_helper=SQL_helper, client=client,
                                        max_workers=threads, file_args=file_args, runtime_args=runtime_args)

    for downloader in downloaders:
        await downloader.download_content()


async def director(args: argparse.Namespace):
    await clear()
    await log(f"We are running version {VERSION} of Cyberdrop Downloader", Fore.WHITE)

    auth_args, file_args, jdownloader_args, runtime_args = await handle_args(args)

    input_file = file_args['input_file']
    if not input_file.is_file():
        input_file.touch()
        await log(f"{input_file} created. Populate it and retry.")
        exit(1)

    client = Client(runtime_args['ratelimit'], runtime_args['throttle'])
    SQL_helper = SQLHelper(runtime_args['ignore_history'], file_args['db_file'])
    await SQL_helper.sql_initialize()

    threads = runtime_args['threads'] if runtime_args['threads'] != 0 else multiprocessing.cpu_count()

    links = args.links
    links = list(map(URL, links))

    with open(input_file, "r", encoding="utf8") as f:
        links += await regex_links(f.read())
    links = list(filter(None, links))

    if not links:
        await log("No links found, check the URL.txt\nIf the link works in your web browser, "
                  "please open an issue ticket with me.", Fore.RED)

    if runtime_args['output_last_forum_post']:
        output_url_file = file_args['output_last_forum_post_file']
        if output_url_file.exists():
            output_url_file.unlink()
            output_url_file.touch()

    await download_all(auth_args=auth_args, file_args=file_args, jdownloader_args=jdownloader_args,
                       runtime_args=runtime_args, links=links, client=client, SQL_helper=SQL_helper, threads=threads)

    logger.debug("Finished")

    partial_downloads = [str(f) for f in file_args['output_folder'].rglob("*.part") if f.is_file()]
    temp_downloads_check = [str(f) for f in await SQL_helper.get_temp_names() if Path(f).is_file()]

    await log('Purging empty directories')
    await purge_dir(file_args['output_folder'])

    await log('Finished downloading. Enjoy :)')
    if partial_downloads:
        await log('There are partial downloads in the downloads folder.')
    if temp_downloads_check:
        await log('There are partial downloads from this run, please re-run the program.')


def main(args=None):
    if not args:
        args = parse_args()
    logging.basicConfig(
        filename=args.log_file,
        level=logging.DEBUG,
        format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
        filemode="w"
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(director(args))
        loop.run_until_complete(asyncio.sleep(5))
    except RuntimeError:
        pass


if __name__ == '__main__':
    print("""STOP! If you're just trying to download files, check the README.md file for instructions.
    If you're developing this project, use start.py instead.""")
    exit()
