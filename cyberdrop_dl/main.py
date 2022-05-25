import argparse
import asyncio
import logging
from pathlib import Path
from argparse import Namespace

from colorama import Fore
from yarl import URL

from . import __version__ as VERSION
from .utils.base_functions import clear, log, logger, purge_dir, regex_links
from .utils.data_classes import AuthData
from .utils.downloaders import get_downloaders
from .utils.scraper import scrape
from .utils.sql_helper import SQLHelper


def parse_args():
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("-i", "--input-file", type=Path, help="file containing links to download", default="URLs.txt")
    parser.add_argument("-o", "--output-folder", type=Path, help="folder to download files to", default="Downloads")
    parser.add_argument("--log-file", help="log file to write to", default="downloader.log")
    parser.add_argument("--db-file", help="history database file to write to",
                        default="download_history.sqlite")
    parser.add_argument("--threads", type=int, help="number of threads to use (0 = max)", default=0)
    parser.add_argument("--attempts", type=int, help="number of attempts to download each file", default=10)
    parser.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    parser.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    parser.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    parser.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    parser.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    parser.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    parser.add_argument("--ignore-history", help="This ignores previous download history", action="store_true")
    parser.add_argument("--separate-posts", help="separates thotsbay scraping into folders by post",
                        action="store_true")
    parser.add_argument("--thotsbay-username", type=str, help="username to login to thotsbay", default=None)
    parser.add_argument("--thotsbay-password", type=str, help="password to login to thotsbay", default=None)
    parser.add_argument("links", metavar="link", nargs="*",
                        help="link to content to download (passing multiple links is supported)", default=[])
    args = parser.parse_args()
    return args


async def download_all(args: argparse.Namespace):
    await clear()
    await log(f"We are running version {VERSION} of Cyberdrop Downloader", Fore.WHITE)
    print_args = Namespace(**vars(args)).__dict__
    print_args['thotsbay_password'] = '!REDACTED!'
    logging.debug(f"Starting downloader with args: {print_args}")
    input_file = args.input_file
    if not input_file.is_file():
        input_file.touch()
        await log(f"{input_file} created. Populate it and retry.")
        exit(1)

    SQL_helper = SQLHelper(args.ignore_history, args.db_file)
    await SQL_helper.sql_initialize()

    links = args.links
    links = list(map(URL, links))

    with open(input_file, "r", encoding="utf8") as f:
        links += await regex_links(f.read())
    thotsbay_auth = AuthData(args.thotsbay_username, args.thotsbay_password)
    content_object = await scrape(links, args.include_id, thotsbay_auth, args.separate_posts)
    if await content_object.is_empty():
        logging.error(f'ValueError No links')
        await log("No links found, check the URL.txt\nIf the link works in your web browser, "
                  "please open an issue ticket with me.", Fore.RED)
        await log("This program does not currently support password protected albums.", Fore.RED)
        exit(0)
    await clear()
    downloaders = await get_downloaders(content_object, folder=args.output_folder, attempts=args.attempts,
                                        disable_attempt_limit=args.disable_attempt_limit,
                                        threads=args.threads, exclude_videos=args.exclude_videos,
                                        exclude_images=args.exclude_images, exclude_audio=args.exclude_audio,
                                        exclude_other=args.exclude_other, SQL_helper=SQL_helper)

    for downloader in downloaders:
        await downloader.download_content()
    logger.debug("Finished")

    partial_downloads = [f for f in args.output_folder.glob("*.part") if f.is_file()]
    combined = '\t'.join(partial_downloads)

    await log('Purging empty directories')
    await purge_dir(args.output_folder)

    await log('Finished downloading. Enjoy :)')
    if partial_downloads:
        await log('There are still partial downloads in your folders, please re-run the program.')


def main(args=None):
    if not args:
        args = parse_args()
    logging.basicConfig(
        filename=args.log_file,
        level=logging.DEBUG,
        format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
        filemode="w"
    )
    asyncio.get_event_loop().run_until_complete(download_all(args))


if __name__ == '__main__':
    print("""
    STOP! If you're just trying to download files, check the README.md file for instructions.
    If you're developing this project, use start.py instead.
    """)
    exit()
