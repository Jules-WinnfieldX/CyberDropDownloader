import json
import re
from pathlib import Path

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, FILE_FORMATS, get_filename_and_ext
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class BunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        album_obj = AlbumItem("Bunkr Loose Items", [])

        cdn_possibilities = r"(?:cdn.bunkr...|cdn..bunkr...|cdn...bunkr...|media-files.bunkr...|media-files..bunkr...|media-files...bunkr...)"
        ext = '.' + url.parts[-1].split('.')[-1]
        if ext:
            ext = ext.lower()
        if ext in FILE_FORMATS['Videos']:
            url = URL(re.sub(cdn_possibilities, "stream.bunkr.su/v", str(url)))
        elif ext in FILE_FORMATS['Images']:
            await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

            check_complete = await self.SQL_Helper.check_complete_singular("bunkr", url.path)
            url = URL(str(url).replace("https://cdn", "https://i"))

            filename, ext = await get_filename_and_ext(url.name)
            media_item = MediaItem(url, url, check_complete, filename, ext)
            await album_obj.add_media(media_item)
            await self.SQL_Helper.insert_album("bunkr", url.path, album_obj)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return album_obj
        elif ext:
            url = URL(re.sub(cdn_possibilities, "files.bunkr.su/d", str(url)))

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        if "stream.bunkr." in url.host or "files.bunkr." in url.host:
            media = await self.get_file(session, url)
            if not media.filename:
                return album_obj
            await album_obj.add_media(media)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            if not media.complete:
                await self.SQL_Helper.insert_media("bunkr", media.url.path, "", str(url), "", "", media.filename, 0)
            return album_obj

        album_obj = await self.get_album(session, url)
        await self.SQL_Helper.insert_album("bunkr", url.path, album_obj)

        if album_obj.media:
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj

    async def get_file(self, session: ScrapeSession, url: URL):
        try:
            soup = await session.get_BS4(url)
            json_obj = json.loads(soup.select_one("script[id=__NEXT_DATA__]").get_text())

            # json_fetch = URL("https://" + url.host + "/_next/data/" + build_id + url.path + '.json')
            # json_obj = await session.get_json(json_fetch)
            # link = URL(json_obj['pageProps']['file']['mediafiles'] + '/' + json_obj['pageProps']['file']['name'])

            json_obj = json_obj['props']
            filename, ext = await get_filename_and_ext(json_obj['pageProps']['file']['name'])
            link = URL(json_obj['pageProps']['file']['mediafiles'] + '/' + json_obj['pageProps']['file']['name'])
            complete = await self.SQL_Helper.check_complete_singular("bunkr", link.path)
            if complete:
                media = MediaItem(link, url, True, filename, ext)
                return media
            media = MediaItem(link, url, False, filename, ext)
            return media

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return MediaItem(url, url, False, "", "")

    async def get_album(self, session: ScrapeSession, url: URL):
        try:
            existing = await self.SQL_Helper.get_existing_album("bunkr", url.path)
            completed_files = []
            album = AlbumItem(url.name, [])
            if existing:
                title = Path(existing[0][-4]).name
                await album.set_new_title(title)
                for file in existing:
                    if file[-1] == 1:
                        completed_files.append(file[-2])

            soup = await session.get_BS4(url)
            json_obj = json.loads(soup.select_one("script[id=__NEXT_DATA__]").get_text())
            json_obj = json_obj['props']
            title = await make_title_safe(json_obj['pageProps']['album']['name'])
            await album.set_new_title(title)
            for file in json_obj['pageProps']['album']['files']:
                try:
                    filename, ext = await get_filename_and_ext(file['name'])
                except NoExtensionFailure:
                    continue

                if ext in FILE_FORMATS['Videos']:
                    cdn_loc = file['cdn']
                    media_loc = cdn_loc.replace('cdn', 'media-files')
                    referrer = "https://stream.bunkr.ru/v/" + file['name']
                    link = URL(media_loc + '/' + file['name'])
                elif ext in FILE_FORMATS['Images']:
                    link = URL(file['i'] + '/' + file['name'])
                    referrer = url
                else:
                    cdn_loc = file['cdn']
                    media_loc = cdn_loc.replace('cdn', 'media-files')
                    referrer = "https://files.bunkr.ru/d/" + file['name']
                    link = URL(media_loc + '/' + file['name'])

                if "12" in link.host:
                    link = link.with_host(url.host.replace('.ru', '.la').replace('.su', '.la'))

                completed = False
                if filename in completed_files:
                    completed = True
                media = MediaItem(link, referrer, completed, filename, ext)
                await album.add_media(media)
            return album

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return None
