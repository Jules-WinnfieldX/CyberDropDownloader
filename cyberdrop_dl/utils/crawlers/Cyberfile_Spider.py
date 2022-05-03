import requests

from colorama import Fore
from yarl import URL

from ..base_functions import log
from ..data_classes import AuthData, DomainItem


class CyberfileCrawler:
    def __init__(self, auth: AuthData):
        self.base_url = URL('https://cyberfile.is/api/v2')
        self.username, self.password = (auth.username, auth.password) if auth else (None, None)
        self.token, self.account_id = self.create_account()

    def create_account(self):
        if not self.username or not self.password:
            log("username or password for cyberfile not provided")
            return False, False
        try:
            data = {"username": self.username, "password": self.password}
            res = requests.get(str(self.base_url/'authorize'), params=data)
            res.raise_for_status()
            res_json = res.json()
            if res_json["_status"] == "success":
                return res_json["data"]["access_token"], res_json["data"]["account_id"]
            else:
                raise requests.exceptions.RequestException(f'status: {res_json["_status"]}')
        except requests.exceptions.RequestException as e:
            log("Couldn't log into cyberfile")

    async def fetch(self, url: URL):
        domain_obj = DomainItem('cyberfile.is', {})
        if not self.username or not self.password or not self.account_id or not self.token:
            await log("Not logged into Cyberfile, skipping " + str(url))
            return domain_obj
        results = []
        await log("Starting scrape of " + str(url), Fore.WHITE)
        if 'folder' in url.parts:
            results.extend(await self.get_folder(url))
        else:
            await log("Skipping " + str(url) + " We can't currently handle single file links through the API")
        if results:
            for result in results:
                title, ret_url = result
                await domain_obj.add_to_album(title, ret_url, url)

        await log("Finished scrape of " + str(url), Fore.WHITE)
        return domain_obj

    async def get_folder(self, url: URL):
        try:
            data = {"access_token": self.token, "account_id": self.account_id, "parent_folder_id": url.parts[2]}
            res = requests.get(str(self.base_url / 'folder/listing'), params=data)
            res.raise_for_status()
            res_json = res.json()
            if res_json["_status"] == "success":
                for folder in res_json['data']['folders']:
                    if folder['folderName'] == url.parts[3]:
                        return await self.extract_folder(folder['id'], folder['folderName'])
            else:
                raise requests.exceptions.RequestException(f'status: {res_json["_status"]}')
        except requests.exceptions.RequestException as e:
            await log(e)

    async def extract_folder(self, id: int, title=None):
        results = []
        try:
            data = {"access_token": self.token, "account_id": self.account_id, "parent_folder_id": id}
            res = requests.get(str(self.base_url / 'folder/listing'), params=data)
            res.raise_for_status()
            res_json = res.json()
            if res_json["_status"] == "success":
                for folder in res_json['data']['folders']:
                    results.extend(await self.extract_folder(folder['id'], title+'/'+folder['folderName']))
                for file in res_json['data']['files']:
                    results.append((title, await self.download_link(file['id'])))
                return results
            else:
                raise requests.exceptions.RequestException(f'status: {res_json["_status"]}')
        except requests.exceptions.RequestException as e:
            await log(e)

    async def download_link(self, id: int):
        try:
            data = {"access_token": self.token, "account_id": self.account_id, "file_id": id}
            res = requests.get(str(self.base_url / 'file/download'), params=data)
            res.raise_for_status()
            res_json = res.json()
            if res_json["_status"] == "success":
                return URL(res_json['data']['download_url'])
            else:
                raise requests.exceptions.RequestException(f'status: {res_json["_status"]}')
        except requests.exceptions.RequestException as e:
            await log(e)