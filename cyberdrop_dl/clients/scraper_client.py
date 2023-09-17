from __future__ import annotations

import aiohttp
from functools import wraps
from typing import TYPE_CHECKING

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from cyberdrop_dl.clients.errors import InvalidContentTypeFailure

if TYPE_CHECKING:
    from yarl import URL

    from cyberdrop_dl.managers.client_manager import ClientManager


def limiter(func):
    """Wrapper handles limits for scrape session"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        domain_limiter = await self.client_manager.get_rate_limiter(args[0])
        async with self.client_manager.session_limit:
            await self._global_limiter.acquire()
            await domain_limiter.acquire()

            async with aiohttp.ClientSession(headers=self.headers, raise_for_status=False,
                                             cookie_jar=self.client_manager.cookies, timeout=self._timeouts) as client:
                kwargs['client_session'] = client
                return await func(self, *args, **kwargs)
    return wrapper


class ScraperClient:
    """AIOHTTP operations for scraping"""
    def __init__(self, client_manager: ClientManager) -> None:
        self.client_manager = client_manager
        self._headers = {"user-agent": client_manager.user_agent}
        self._timeouts = aiohttp.ClientTimeout(total=client_manager.connection_timeout + 60,
                                               connect=client_manager.connection_timeout)
        self._global_limiter = self.client_manager.global_rate_limiter

    @limiter
    async def get_BS4(self, domain: str, url: URL, client_session: ClientSession) -> BeautifulSoup:
        """Returns a BeautifulSoup object from the given URL"""
        async with client_session.get(url, headers=self._headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as response:
            await self.client_manager.check_http_status(response.status, response.headers, response.url)
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if not any(s in content_type.lower() for s in ("html", "text")):
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")
            text = await response.text()
            return BeautifulSoup(text, 'html.parser')
