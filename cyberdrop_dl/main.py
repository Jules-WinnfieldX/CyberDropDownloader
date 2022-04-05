import argparse
import asyncio
import pathlib
from pathlib import Path

from . import __version__ as VERSION
from .utils.scraper import scrape
from .utils.downloaders import get_downloaders
from .utils.base_functions import *


def parse_args():
    parser = argparse.ArgumentParser(description="Bulk downloader for multiple file hosts")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument("-i", "--input-file", help="file containing links to download", default="URLs.txt")
    parser.add_argument("-o", "--output-folder", help="folder to download files to", default="Downloads")
    parser.add_argument("--log-file", help="log file to write to", default="downloader.log")
    parser.add_argument("--threads", type=int, help="number of threads to use (0 = max)", default=0)
    parser.add_argument("--attempts", type=int, help="number of attempts to download each file", default=10)
    parser.add_argument("--disable-attempt-limit", help="disables the attempt limitation", action="store_true")
    parser.add_argument("--include-id", help="include the ID in the download folder name", action="store_true")
    parser.add_argument("--exclude-videos", help="skip downloading of video files", action="store_true")
    parser.add_argument("--exclude-images", help="skip downloading of image files", action="store_true")
    parser.add_argument("--exclude-audio", help="skip downloading of audio files", action="store_true")
    parser.add_argument("--exclude-other", help="skip downloading of images", action="store_true")
    parser.add_argument("--thotsbay-username", type=str, help="username to login to thotsbay", default=None)
    parser.add_argument("--thotsbay-password", type=str, help="password to login to thotsbay", default=None)
    parser.add_argument("links", metavar="link", nargs="*", help="link to content to download (passing multiple links is supported)", default=[])
    args = parser.parse_args()
    return args


async def download_all(args: argparse.Namespace):
    clear()
    log(f"We are running version {VERSION} of Cyberdrop Downloader", Fore.WHITE)
    logging.debug(f"Starting downloader with args: {args.__dict__}")
    input_file = Path(args.input_file)
    if not os.path.isfile(input_file):
        Path.touch(input_file)
        log(f"{input_file} created. Populate it and retry.")
        exit(1)

    links = args.links
    with open(input_file, "r") as f:
        links += regex_links(f.read())
    content_object = await scrape(links, args.include_id, args.thotsbay_username, args.thotsbay_password)
    if content_object.is_empty():
        logging.error(f'ValueError No links')
        log('No links found, check the URL.txt\nIf the link works in your web browser, '
            'please open an issue ticket with me.', Fore.RED)
        log("This program does not currently support password protected albums.", Fore.RED)
        exit(0)
    clear()
    downloaders = get_downloaders(content_object, folder=Path(args.output_folder), attempts=args.attempts,
                                  disable_attempt_limit=args.disable_attempt_limit,
                                  threads=args.threads, exclude_videos=args.exclude_videos,
                                  exclude_images=args.exclude_images, exclude_audio=args.exclude_audio,
                                  exclude_other=args.exclude_other)

    for downloader in downloaders:
        await downloader.download_content()
    logger.debug("Finished")

    all_files = [str(f) for f in pathlib.Path(args.output_folder).glob("**/*") if f.is_file()]
    combined = '\t'.join(all_files)

    log('Finished downloading. Enjoy :)')
    if '.part' in combined:
        log('There are still partial downloads in your folders, please re-run the program.')


def main():
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
