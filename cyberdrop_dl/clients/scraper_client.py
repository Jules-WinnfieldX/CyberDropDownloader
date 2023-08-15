import aiohttp
from aiolimiter import AsyncLimiter

from cyberdrop_dl.managers.client_manager import ClientManager


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