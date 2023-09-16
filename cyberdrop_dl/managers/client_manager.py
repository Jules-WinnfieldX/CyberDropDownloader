from __future__ import annotations

import asyncio
import ssl
from enum import IntEnum
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
import certifi
from aiolimiter import AsyncLimiter
from multidict import CIMultiDictProxy
from yarl import URL

from cyberdrop_dl.clients.errors import DownloadFailure
from cyberdrop_dl.clients.scraper_client import ScraperClient

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class CustomHTTPStatus(IntEnum):
    WEB_SERVER_IS_DOWN = 521
    IM_A_TEAPOT = 418
    DDOS_GUARD = 429


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
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if self.verify_ssl else False
        self.cookies = aiohttp.CookieJar(quote_cookie=False)
        self.proxy = manager.config_manager.global_settings_data['General']['proxy']

        self.domain_rate_limits = {
            "bunkr": AsyncLimiter(10, 1),

            "other": AsyncLimiter(100, 1)
        }
        self.global_rate_limiter = AsyncLimiter(self.rate_limit, 1)
        self.session_limit = asyncio.Semaphore(50)

        self.scraper_sessions = {}
        self.downloader_sessions = {}

    async def get_scraper_session(self, domain: str) -> ScraperClient:
        """Get a scraper session"""
        if domain in self.scraper_sessions:
            return self.scraper_sessions[domain]
        self.scraper_sessions[domain] = ScraperClient(self)
        return self.scraper_sessions[domain]

    async def get_downloader_session(self, domain: str) -> ScraperClient:
        """Get a downloader session"""
        if domain in self.downloader_sessions:
            return self.downloader_sessions[domain]
        self.downloader_sessions[domain] = ScraperClient(self)
        return self.downloader_sessions[domain]

    async def close(self) -> None:
        """Close all sessions"""
        for session in self.scraper_sessions.values():
            await session.client_session.close()
        for session in self.downloader_sessions.values():
            await session.client_session.close()

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
        if headers.get("Server") == "ddos-guard":
            raise DownloadFailure(status=CustomHTTPStatus.DDOS_GUARD, message="DDoS-Guard detected, unable to continue")
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

        raise DownloadFailure(status=status, message=f"HTTP status code {status}: {HTTPStatus(status).phrase}")