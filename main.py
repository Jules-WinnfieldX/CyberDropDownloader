import logging
import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from utils.downloaders import get_downloaders
from utils.scrapers import get_scrapper

logging.basicConfig(
    level=logging.DEBUG,
    filename='logs.log',
    format='%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s'
)

SUPPORTED_URLS = {'cyberdrop.me', 'bunkr.is', 'pixl.is', 'putme.ga'}

FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.gif', '.webp', '.jpe', '.svg',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg'
    }
}


def classify_media_files(path: Path) -> None:
    """Sort out files and videos to their own directories.

    Args:
        path (Path): Path containing both images and files to be classified.
    """

    images = [filename for filename in path.iterdir() if filename.suffix in FILE_FORMATS['Images']]
    videos = [filename for filename in path.iterdir() if filename.suffix in FILE_FORMATS['Videos']]

    if not images or not videos:
        return

    images_folder = Path(path / 'Images')
    images_folder.mkdir(exist_ok=True)
    videos_folder = Path(path / 'Videos')
    videos_folder.mkdir(exist_ok=True)

    # Move the images and videos to appropriate directories
    for image in images:
        image.rename(images_folder / image.name)
    for video in videos:
        video.rename(videos_folder / video.name)


def parse_args() -> argparse.Namespace:
    """Parse out the command line arguments."""
    parser = argparse.ArgumentParser(
        description='Simple Script written in Python for download galleries of images / videos',
        epilog="Enjoy!!!"
    )
    parser.add_argument(
        '-u', '--url',
        help=f'The url which contains images or videos. Supported links: {", ".join(SUPPORTED_URLS)}',
        required=False,
        action='store'
    )
    parser.add_argument(
        '-p', '--progress',
        help='Show progress bar from each url. By default its False',
        action='store_true'
    )
    parser.add_argument(
        '-w', '--max-workers',
        help='Define the maximum amount of workers for downloading.',
        default=20,
        type=int
    )

    args = parser.parse_args()
    if args.url:
        if not urlparse(args.url).netloc in SUPPORTED_URLS:
            logging.error(f'Unsupported URL:{args.url}')
            raise ValueError('Unsupported URL link!')
    return args


async def main() -> None:
    args = parse_args()
    if args.url:
        scrapper = get_scrapper(args.url)
        with scrapper:
            title = scrapper.get_soup().select_one('title').text
            links = scrapper.result_links()
            if not links:
                logging.error(f'ValueError No links: {links}')
                raise ValueError('No links found, check the URL.')

        downloaders = get_downloaders(links, folder=Path(
            title), max_workers=args.max_workers)

        for downloader in downloaders:
            await downloader.download_content(show_progress=args.progress)
        classify_media_files(Path(title))


if __name__ == '__main__':
    asyncio.run(main())


# TODO: Re-add a way to redownload failed URLs and perhaps log them with the use of logging library
