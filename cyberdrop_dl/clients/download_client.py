from typing import Dict

import aiohttp
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.managers.client_manager import ClientManager


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
        self.bunkr_maintenance = [URL("https://bnkr.b-cdn.net/maintenance-vid.mp4"), URL("https://bnkr.b-cdn.net/maintenance.mp4")]
