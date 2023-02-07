from pathlib import Path

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, get_filename_and_ext, \
    get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class CyberdropCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.SQL_Helper = SQL_Helper
        self.quiet = quiet

    async def fetch(self, session: ScrapeSession, url: URL):
        album_obj = AlbumItem("Cyberdrop Loose Files", [])

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
        if await check_direct(url):
            url_path = await get_db_path(url)
            complete = await self.SQL_Helper.check_complete_singular("cyberdrop", url_path)
            filename, ext = await get_filename_and_ext(url.name)
            media = MediaItem(url, url, complete, filename, ext)
            await album_obj.add_media(media)
            await self.SQL_Helper.insert_album("cyberdrop", "", album_obj)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return album_obj

        try:
            url_path = await get_db_path(url)
            existing = await self.SQL_Helper.get_existing_album("cyberdrop", url_path)
            existing_files = []
            if existing:
                title = Path(existing[0][-4]).name
                await album_obj.set_new_title(title)
                all_complete = True
                for file in existing:
                    if file[-1] == 1:
                        existing_files.append(file[-2])
                        media = MediaItem(url, url, True, file[-2], "." + file[-2].rsplit('.')[-1])
                        await album_obj.add_media(media)
                    else:
                        all_complete = False
                if all_complete:
                    return album_obj

            soup = await session.get_BS4(url)

            title = soup.select_one("h1[id=title]").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                titlep2 = [s for s in titlep2 if "." in s][-1]
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())
            await album_obj.set_new_title(title)

            links = soup.select('div[class="image-container column"] a')
            for link in links:
                link = URL(link.get('href'))
                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    continue

                if filename in existing_files:
                    continue
                media = MediaItem(link, url, False, filename, ext)
                await album_obj.add_media(media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return album_obj

        url_path = await get_db_path(url)
        await self.SQL_Helper.insert_album("cyberdrop", url_path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj
