from __future__ import annotations

import aiohttp
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup

from cyberdrop_dl.clients.errors import InvalidContentTypeFailure

if TYPE_CHECKING:
    from yarl import URL

    from cyberdrop_dl.managers.client_manager import ClientManager


def scrape_limit(func):
    """Wrapper handles limits for scrape session"""

    async def wrapper(self, *args, **kwargs):
        async with self.client.simultaneous_session_limit:
            async with self.rate_limiter:
                return await func(self, *args, **kwargs)

    return wrapper


class ScraperClient:
    """AIOHTTP operations for scraping"""
    def __init__(self, client_manager: ClientManager) -> None:
        self.client_manager = client_manager
        self.rate_limiter = AsyncLimiter(client_manager.rate_limit, 1)
        self.headers = {"user-agent": client_manager.user_agent}
        self.timeouts = aiohttp.ClientTimeout(total=client_manager.connection_timeout + 60,
                                              connect=client_manager.connection_timeout)
        self.client_session = aiohttp.ClientSession(headers=self.headers, raise_for_status=True,
                                                    cookie_jar=client_manager.cookies, timeout=self.timeouts)

    @scrape_limit
    async def get_BS4(self, url: URL) -> BeautifulSoup:
        async with self.client_session.get(url, ssl=self.client_manager.ssl_context) as response:
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if not any(s in content_type.lower() for s in ("html", "text")):
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")
            text = await response.text()
            return BeautifulSoup(text, 'html.parser')
