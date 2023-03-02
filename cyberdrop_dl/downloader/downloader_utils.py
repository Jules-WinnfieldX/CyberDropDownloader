import shutil
from base64 import b64encode
from http import HTTPStatus
from pathlib import Path

from cyberdrop_dl.base_functions.base_functions import FILE_FORMATS
from cyberdrop_dl.base_functions.data_classes import MediaItem


async def allowed_filetype(media: MediaItem, block_images: bool, block_video: bool, block_audio: bool, block_other: bool):
    """Checks whether the enclosed file is allowed to be downloaded"""
    ext = media.ext
    if block_images:
        if ext in FILE_FORMATS["Images"]:
            return False
    if block_video:
        if ext in FILE_FORMATS["Videos"]:
            return False
    if block_audio:
        if ext in FILE_FORMATS["Audio"]:
            return False
    if block_other:
        if ext not in FILE_FORMATS["Images"] and ext not in FILE_FORMATS["Videos"] and ext not in FILE_FORMATS["Audio"]:
            return False
    return True


async def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


async def check_free_space(required_space_gb: int, download_directory: Path) -> bool:
    """Checks if there is enough free space on the drive to continue operating"""
    free_space = shutil.disk_usage(download_directory.parent).free
    free_space_gb = free_space / 1024 ** 3
    return free_space_gb >= required_space_gb


async def is_4xx_client_error(status_code: int) -> bool:
    """Checks whether the HTTP status code is 4xx client error"""
    return HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR
