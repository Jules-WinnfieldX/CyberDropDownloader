from __future__ import annotations

import json

import aiohttp
from functools import wraps
from typing import TYPE_CHECKING, Dict, Optional

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from multidict import CIMultiDictProxy
from yarl import URL

from cyberdrop_dl.clients.errors import InvalidContentTypeFailure

if TYPE_CHECKING:
    from cyberdrop_dl.managers.client_manager import ClientManager


def limiter(func):
    """Wrapper handles limits for scrape session"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        domain_limiter = await self.client_manager.get_rate_limiter(args[0])
        async with self.client_manager.session_limit:
            await self._global_limiter.acquire()
            await domain_limiter.acquire()

            async with aiohttp.ClientSession(headers=self._headers, raise_for_status=False,
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
            await self.client_manager.check_http_status(response)
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if not any(s in content_type.lower() for s in ("html", "text")):
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")
            text = await response.text()
            return BeautifulSoup(text, 'html.parser')

    @limiter
    async def get_BS4_and_return_URL(self, domain: str, url: URL, client_session: ClientSession) -> tuple[BeautifulSoup, URL]:
        """Returns a BeautifulSoup object and response URL from the given URL"""
        async with client_session.get(url, headers=self._headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as response:
            await self.client_manager.check_http_status(response)
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if not any(s in content_type.lower() for s in ("html", "text")):
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting text")
            text = await response.text()
            return BeautifulSoup(text, 'html.parser'), URL(response.url)

    @limiter
    async def get_json(self, domain: str, url: URL, params: Optional[Dict] = None, headers_inc: Optional[Dict] = None, client_session: ClientSession = None) -> Dict:
        """Returns a JSON object from the given URL"""
        headers = {**self._headers, **headers_inc} if headers_inc else self._headers

        async with client_session.get(url, headers=headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy, params=params) as response:
            await self.client_manager.check_http_status(response)
            content_type = response.headers.get('Content-Type')
            assert content_type is not None
            if 'json' not in content_type.lower():
                raise InvalidContentTypeFailure(message=f"Received {content_type}, was expecting JSON")
            return await response.json()

    @limiter
    async def get_text(self, domain: str, url: URL, client_session: ClientSession) -> str:
        """Returns a text object from the given URL"""
        async with client_session.get(url, headers=self._headers, ssl=self.client_manager.ssl_context,
                                      proxy=self.client_manager.proxy) as response:
            text = await response.text()
            await self.client_manager.check_http_status(response)
            return text

    @limiter
    async def post_data(self, domain: str, url: URL, client_session: ClientSession, data: Dict, req_resp: bool = True) -> Dict:
        """Returns a JSON object from the given URL when posting data"""
        async with client_session.post(url, headers=self._headers, ssl=self.client_manager.ssl_context,
                                       proxy=self.client_manager.proxy, data=data) as response:
            await self.client_manager.check_http_status(response)
            if req_resp:
                return json.loads(await response.content.read())
            else:
                return {}

    @limiter
    async def get_head(self, domain: str, url: URL, client_session: ClientSession) -> CIMultiDictProxy[str]:
        """Returns the headers from the given URL"""
        async with client_session.head(url, headers=self._headers, ssl=self.client_manager.ssl_context,
                                       proxy=self.client_manager.proxy) as response:
            return response.headers
