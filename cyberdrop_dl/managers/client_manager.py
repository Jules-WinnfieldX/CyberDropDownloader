from __future__ import annotations

import asyncio
import ssl
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
import certifi
from aiolimiter import AsyncLimiter
from multidict import CIMultiDictProxy
from yarl import URL

from cyberdrop_dl.clients.download_client import DownloadClient
from cyberdrop_dl.clients.errors import DownloadFailure
from cyberdrop_dl.clients.scraper_client import ScraperClient
from cyberdrop_dl.utils.utilities import CustomHTTPStatus

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class ClientManager:
    """Creates a 'client' that can be referenced by scraping or download sessions"""
    def __init__(self, manager: Manager):
        self.manager = manager

        self.connection_timeout = manager.config_manager.global_settings_data['Rate_Limiting_Options']['connection_timeout']
        self.read_timeout = manager.config_manager.global_settings_data['Rate_Limiting_Options']['read_timeout']
        self.rate_limit = manager.config_manager.global_settings_data['Rate_Limiting_Options']['rate_limit']
        self.download_delay = manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_delay']
        self.user_agent = manager.config_manager.global_settings_data['General']['user_agent']
        self.verify_ssl = not manager.config_manager.global_settings_data['General']['allow_insecure_connections']
        self.simultaneous_per_domain = manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']

        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if self.verify_ssl else False
        self.cookies = aiohttp.CookieJar(quote_cookie=False)
        self.proxy = manager.config_manager.global_settings_data['General']['proxy']

        self.domain_rate_limits = {
            "bunkr": AsyncLimiter(5, 1),
            "cyberdrop": AsyncLimiter(10, 1),
            "pixeldrain": AsyncLimiter(10, 1),
            "other": AsyncLimiter(25, 1)
        }
        self.global_rate_limiter = AsyncLimiter(self.rate_limit, 1)
        self.session_limit = asyncio.Semaphore(50)
        self.download_session_limit = asyncio.Semaphore(self.manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'])

        self.scraper_session = ScraperClient(self)
        self.downloader_session = DownloadClient(self)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def get_rate_limiter(self, domain: str) -> AsyncLimiter:
        """Get a rate limiter for a domain"""
        if domain in self.domain_rate_limits:
            return self.domain_rate_limits[domain]
        return self.domain_rate_limits["other"]

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def check_http_status(self, status: int, headers: CIMultiDictProxy, response_url: URL,
                                download: bool = False) -> None:
        """Checks the HTTP status code and raises an exception if it's not acceptable"""
        if not headers.get('Content-Type'):
            raise DownloadFailure(status=CustomHTTPStatus.IM_A_TEAPOT, message="No content-type in response header")

        if download:
            if response_url in [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"),
                                URL("https://bnkr.b-cdn.net/maintenance.mp4")]:
                raise DownloadFailure(status=HTTPStatus.SERVICE_UNAVAILABLE, message="Bunkr under maintenance")
            if "imgur.com/removed" in str(response_url):
                raise DownloadFailure(status=HTTPStatus.NOT_FOUND, message="Imgur image has been removed")

        if HTTPStatus.OK <= status < HTTPStatus.BAD_REQUEST:
            return

        try:
            phrase = HTTPStatus(status).phrase
        except ValueError:
            phrase = "Unknown"

        raise DownloadFailure(status=status, message=f"HTTP status code {status}: {phrase}")
