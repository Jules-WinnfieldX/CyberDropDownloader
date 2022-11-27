from typing import Dict

import aiofiles
import logging
import os
import re
from pathlib import Path

import yaml
from colorama import Fore, Style
from yarl import URL

from .config_schema import config_default, files_args, authentication_args, jdownloader_args, runtime_args

"""This file contains generic information and functions that are used around the program"""

FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.webp', '.jpe', '.svg', '.jfif',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg', '.mkv', '.mts', '.ts',
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a',
    },
    'Other': {
        '.json', '.torrent', '.zip', '.rar',
        '.7z', '.torrent', '.psd', '.pdf',
    }
}

MAX_FILENAME_LENGTH = 100

logger = logging.getLogger(__name__)


class FailureException(Exception):
    """Basic failure exception I can throw to force a retry."""

    def __init__(self, code, message="Something went wrong", rescrape=False):
        self.code = code
        self.message = message
        self.rescrape = rescrape
        super().__init__(self.message)
        super().__init__(self.code)


async def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\']', "", name).strip()


async def log(text, style=Fore.WHITE, quiet=False) -> None:
    logger.debug(text)
    if not quiet:
        print(style + str(text) + Style.RESET_ALL)


async def clear() -> None:
    """Clears the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


async def make_title_safe(title: str):
    title = re.sub(r'[\\*?:"<>|./]', "-", title)
    return title


async def purge_dir(dirname, in_place=True):
    deleted = []
    dir_tree = list(os.walk(dirname, topdown=False))

    for tree_element in dir_tree:
        sub_dir = tree_element[0]
        dir_count = len(os.listdir(sub_dir))
        if dir_count == 0:  # Helps with readability and i've had issues with it deleting non-empty dirs
            deleted.append(sub_dir)

    if in_place:
        list(map(os.rmdir, deleted))


async def regex_links(urls) -> list:
    if urls.lstrip().startswith('#'):
        return []

    all_links = [x.group().replace(".md.", ".") for x in re.finditer(
        r"(?:http.*?)(?=($|\n|\r\n|\r|\s|\"|\[/URL]|]\[|\[/img]))", urls)]
    yarl_links = []
    for link in all_links:
        yarl_links.append(URL(link))
    return yarl_links


async def cyberdrop_parse(url: URL) -> URL:
    mapping_direct = [r'img-...cyberdrop...',
                      r'f.cyberdrop...', r'fs-...cyberdrop...']
    url = str(url)
    for mapping in mapping_direct:
        url = re.sub(mapping, 'cyberdrop.to', url)
    return URL(url)


async def write_last_post_file(file: Path, url: str):
    async with aiofiles.open(file, mode='a') as f:
        await f.write(url + '\n')
    return


async def check_direct(url: URL):
    mapping_direct = [r'i.pixl.li', r'i..pixl.li', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'i.bunkr...', r'i..bunkr...', r'i...bunkr...', r'media-files.bunkr...',
                      r'media-files..bunkr...', r'cdn.bunkr...', r'cdn..bunkr...', r'cdn...bunkr...',
                      r'jpg.church/images/...', r'simp..jpg.church', r's..putmega.com', r's..putme.ga', r'images..imgbox.com' ]
    return any(re.search(domain, url.host) for domain in mapping_direct)


async def is_forum(url: URL):
    mapping_forum = ['simpcity...', 'socialmediagirls....', 'xbunker...']
    return any(re.search(domain, url.host) for domain in mapping_forum)

async def create_config(config: Path, passed_args=None, remake=None):
    if config.is_file() and not remake:
        logging.debug("Validating Config")
        await validate_config(config)
        return

    logging.debug("Creating Config File")
    config_data = config_default
    if passed_args:
        for arg in authentication_args:
            if arg in passed_args.keys():
                config_data[0]["Configuration"]["Authentication"][arg] = passed_args[arg]
        for arg in files_args:
            if arg in passed_args.keys():
                config_data[0]["Configuration"]["Files"][arg] = str(passed_args[arg])
        for arg in jdownloader_args:
            if arg in passed_args.keys():
                config_data[0]["Configuration"]["JDownloader"][arg] = passed_args[arg]
        for arg in runtime_args:
            if arg in passed_args.keys():
                config_data[0]["Configuration"]["Runtime"][arg] = passed_args[arg]

    with open(config, 'w') as yamlfile:
        yaml.dump(config_data, yamlfile)
    return


async def validate_config(config: Path):
    with open(config, "r") as yamlfile:
        data = yaml.load(yamlfile, Loader=yaml.FullLoader)
    data = data[0]["Configuration"]
    recreate = 0
    try:
        if not set(authentication_args).issubset(set(data['Authentication'].keys())):
            recreate = 1
        if not set(files_args).issubset(set(data['Files'].keys())):
            recreate = 1
        if not set(jdownloader_args).issubset(set(data['JDownloader'].keys())):
            recreate = 1
        if not set(runtime_args).issubset(set(data['Runtime'].keys())):
            recreate = 1

        if recreate:
            config.unlink()
            logging.debug("Recreating Config")

            args = {}
            args_list = [data['Authentication'], data['Files'], data['JDownloader'], data['Runtime']]
            for dic in args_list:
                args.update(dic)
            await create_config(config, args, True)

    except KeyError:
        config.unlink()
        await log("Config was malformed, recreating.")
        await create_config(config, None, True)


async def run_args(config: Path, cmd_arg: Dict):
    with open(config, "r") as yamlfile:
        data = yaml.load(yamlfile, Loader=yaml.FullLoader)
    data = data[0]["Configuration"]
    if data['Apply_Config']:
        return data

    logging.debug("Gathering Args")
    config_data = config_default[0]["Configuration"]
    for arg in authentication_args:
        if arg in cmd_arg.keys():
            config_data["Authentication"][arg] = cmd_arg[arg]
    for arg in files_args:
        if arg in cmd_arg.keys():
            config_data["Files"][arg] = cmd_arg[arg]
    for arg in jdownloader_args:
        if arg in cmd_arg.keys():
            config_data["JDownloader"][arg] = cmd_arg[arg]
    for arg in runtime_args:
        if arg in cmd_arg.keys():
            config_data["Runtime"][arg] = cmd_arg[arg]
    return config_data
