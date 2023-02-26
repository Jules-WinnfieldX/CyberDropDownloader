from yarl import URL

from ..base_functions.base_functions import log, logger, get_filename_and_ext, get_db_path
from ..base_functions.data_classes import MediaItem, AlbumItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class AnonfilesCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.api_link = URL("https://api.anonfiles.com/v2/file")

    async def fetch(self, session: ScrapeSession, url: URL):
        """Scraper for Anonfiles"""
        if 'cdn' in url.host:
            url = URL("https://anonfiles.com") / url.parts[1]

        album_obj = AlbumItem("Loose Anon Files", [])

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        try:
            json = await session.get_json(self.api_link/url.parts[1]/"info")
            if json['status']:
                soup = await session.get_BS4(url)

                link = soup.select_one("a[id=download-url]")
                link = URL(link.get('href'))

                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("anonfiles", url_path)

                filename, ext = await get_filename_and_ext(".".join(json['data']['file']['metadata']['name'].rsplit("_", 1)))
                media_item = MediaItem(link, url, complete, filename, ext, filename)
                await album_obj.add_media(media_item)
                if not complete:
                    await self.SQL_Helper.insert_media("anonfiles", url_path, "", str(url), "", "", filename, 0)
            else:
                await log(f"[red]Dead: {str(url)}[/red]", quiet=self.quiet)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return album_obj

        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj
