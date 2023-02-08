from yarl import URL

from ..base_functions.base_functions import log, logger, get_db_path, get_filename_and_ext
from ..base_functions.data_classes import DomainItem, AlbumItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class PostImgCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        album_obj = AlbumItem("Loose PostImg Files", [])
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        try:
            if "gallery" in url.parts:
                content = await self.get_folder(session, url)
                for media_item in content:
                    await album_obj.add_media(media_item)
            else:
                media_item = await self.get_singular(session, url)
                await album_obj.add_media(media_item)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

        await self.SQL_Helper.insert_album("postimg", url.path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj

    async def get_folder(self, session: ScrapeSession, url: URL):
        album = url.raw_name
        data = {"action": "list", "album": album}
        content = []
        i = 1
        while True:
            data_used = data
            data_used["page"] = i
            data_out = await session.post(URL("https://postimg.cc/json"), data_used)
            if data_out['status_code'] != 200 or not data_out['images']:
                break
            for item in data_out['images']:
                referrer = URL("https://postimg.cc/" + item[0])
                img = URL(item[4].replace(item[0], item[1]))

                filename, ext = await get_filename_and_ext(img.name)
                url_path = await get_db_path(img)
                complete = await self.SQL_Helper.check_complete_singular("postimg", url_path)
                media_item = MediaItem(img, referrer, complete, filename, ext)

                content.append(media_item)
            i += 1
        return content

    async def get_singular(self, session: ScrapeSession, url: URL):
        soup = await session.get_BS4(url)
        link = URL(soup.select_one("a[id=download]").get('href').replace("?dl=1", ""))

        filename, ext = await get_filename_and_ext(link.name)
        url_path = await get_db_path(link)
        complete = await self.SQL_Helper.check_complete_singular("postimg", url_path)
        media_item = MediaItem(link, url, complete, filename, ext)

        return media_item
