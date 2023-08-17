from __future__ import annotations

import copy
from enum import IntEnum
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import DownloadFailure

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.client_manager import ClientManager
    from cyberdrop_dl.utils.dataclasses.url_objects import MediaItem


class CustomHTTPStatus(IntEnum):
    WEB_SERVER_IS_DOWN = 521
    IM_A_TEAPOT = 418


async def is_4xx_client_error(status_code: int) -> bool:
    """Checks whether the HTTP status code is 4xx client error"""
    return HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR


class DownloadClient:
    """AIOHTTP operations for downloading"""
    def __init__(self, client_manager: ClientManager):
        self.client_manager = client_manager
        self.headers = {"user-agent": client_manager.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=client_manager.read_timeout + client_manager.connection_timeout,
                                              connect=client_manager.connection_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=client_manager.cookies, timeout=self.timeouts)
        self.throttle_times: Dict[str, float] = {}
        self.bunkr_maintenance = [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"),
                                  URL("https://bnkr.b-cdn.net/maintenance.mp4")]

    async def get_filesize(self, media_item: MediaItem) -> int:
        """Returns the file size of the media item"""
        headers = copy.deepcopy(self.headers)
        headers['Referer'] = media_item.referer

        async with self.client_session.get(media_item.url, headers=headers, ssl=self.client_manager.ssl_context,
                                           raise_for_status=False) as resp:
            if resp.status > 206:
                if "Server" in resp.headers:
                    if resp.headers["Server"] == "ddos-guard":
                        raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT,
                                              message="DDoS-Guard detected, unable to download")
                raise DownloadFailure(status=resp.status, message=f"Unexpected status code {resp.status} from {media_item.url}")
            return int(resp.headers.get('Content-Length', '0'))
