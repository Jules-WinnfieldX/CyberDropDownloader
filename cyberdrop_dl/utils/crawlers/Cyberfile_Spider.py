import requests
import json

from colorama import Fore
from yarl import URL

from ..base_functions import log, ssl_context
from ..data_classes import AuthData, DomainItem


class CyberfileCrawler:
    def __init__(self):
        self.base_url = URL('https://cyberfile.is/account/ajax/load_files')

    async def fetch(self, session, url: URL):
        data = {"pageType": "folder", "nodeId": 303, "pageStart": 1, "perPage": 0, "filterOrderBy": ""}
        res = await session.post(str(self.base_url), data=data, headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"}, ssl=ssl_context)
        content = json.loads(await res.content.read())
        print()
