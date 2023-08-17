from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

import aiohttp
import certifi

from cyberdrop_dl.clients.scraper_client import ScraperClient

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
        self.ssl_context = ssl.create_default_context(cafile=certifi.where()) if self.verify_ssl else False
        self.cookies = aiohttp.CookieJar(quote_cookie=False)
        self.proxy = manager.config_manager.global_settings_data['General']['proxy']

        self.scraper_sessions = {}
        self.downloader_sessions = {}

    async def get_scraper_session(self, domain: str):
        """Get a scraper session"""
        if domain in self.scraper_sessions:
            return self.scraper_sessions[domain]
        self.scraper_sessions[domain] = ScraperClient(self)
        return self.scraper_sessions[domain]

    async def get_downloader_session(self, domain: str):
        """Get a downloader session"""
        if domain in self.downloader_sessions:
            return self.downloader_sessions[domain]
        self.downloader_sessions[domain] = ScraperClient(self)
        return self.downloader_sessions[domain]

    async def close(self):
        """Close all sessions"""
        for session in self.scraper_sessions.values():
            await session.client_session.close()
        for session in self.downloader_sessions.values():
            await session.client_session.close()
