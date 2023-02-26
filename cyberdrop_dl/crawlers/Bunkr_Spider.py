import re

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, FILE_FORMATS, get_filename_and_ext, \
    get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class BunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, remove_bunkr_id: bool):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.remove_bunkr_id = remove_bunkr_id

    async def fetch(self, session: ScrapeSession, url: URL):
        """Scraper for Bunkr"""
        album_obj = AlbumItem("Loose Bunkr Files", [])
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        if "v" in url.parts or "d" in url.parts:
            media = await self.get_file(session, url)
            if not media.filename:
                return album_obj
            await album_obj.add_media(media)
            await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            if not media.complete:
                await self.SQL_Helper.insert_media("bunkr", media.url.path, "", str(url), "", "", media.filename, 0)
            return album_obj

        if "a" in url.parts:
            album_obj = await self.get_album(session, url)
            await self.SQL_Helper.insert_album("bunkr", url.path, album_obj)

            if album_obj.media:
                await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
            return album_obj

        cdn_possibilities = r"(?:cdn.bunkr...|cdn..bunkr...|cdn...bunkr...|media-files.bunkr...|media-files..bunkr...|media-files...bunkr...)"
        ext = '.' + url.parts[-1].split('.')[-1]
        if ext:
            ext = ext.lower()
        if ext in FILE_FORMATS['Images']:
            check_complete = await self.SQL_Helper.check_complete_singular("bunkr", url.path)
            url = URL(str(url).replace("https://cdn", "https://i"))

            filename, ext = await get_filename_and_ext(url.name)
            if self.remove_bunkr_id:
                filename = await self.remove_id(filename, ext)

            media_item = MediaItem(url, url, check_complete, filename, ext, filename)
            await album_obj.add_media(media_item)
        else:
            if ext in FILE_FORMATS['Videos']:
                referer = URL(re.sub(cdn_possibilities, "bunkr.su/v", str(url)))
            else:
                referer = URL(re.sub(cdn_possibilities, "bunkr.su/d", str(url)))
            media_item = await self.get_file(session, referer)
            await album_obj.add_media(media_item)

        await self.SQL_Helper.insert_album("bunkr", url.path, album_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return album_obj

    async def remove_id(self, filename: str, ext: str):
        """Removes the additional string bunkr adds to the end of every filename"""
        filename = filename.rsplit(ext, 1)[0]
        filename = filename.rsplit("-", 1)[0]
        if ext not in filename:
            filename = filename + ext
        return filename

    async def check_for_la(self, url: URL):
        if "12" in url.host:
            url_host = url.host.replace(".su", ".la").replace(".ru", ".la")
            url = url.with_host(url_host)
        return url

    async def get_file(self, session: ScrapeSession, url: URL):
        """Gets the media item from the supplied url"""
        try:
            soup = await session.get_BS4(url)
            head = soup.select_one("head")
            scripts = head.select('script[type="text/javascript"]')
            link = None

            for script in scripts:
                if script.text:
                    if "link.href" in script.text:
                        link = script.text.split('link.href = "')[-1].split('";')[0]
                        break
            if not link:
                raise
            link = URL(link)
            link = link.with_name(url.name)
            filename, ext = await get_filename_and_ext(link.name)
            if ext not in FILE_FORMATS['Images']:
                link = await self.check_for_la(link)
            if self.remove_bunkr_id:
                filename = await self.remove_id(filename, ext)

            complete = await self.SQL_Helper.check_complete_singular("bunkr", link.path)
            if complete:
                media = MediaItem(link, url, True, filename, ext, filename)
                return media
            media = MediaItem(link, url, False, filename, ext, filename)
            return media

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return MediaItem(url, url, False, "", "", "")

    async def get_album(self, session: ScrapeSession, url: URL):
        """Iterates through an album and creates the media items"""
        album = AlbumItem(url.name, [])
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
            for elem in title.find_all("span"):
                elem.decompose()
            title = await make_title_safe(title.get_text())
            await album.set_new_title(title)
            for file in soup.select('a[class*="grid-images_box-link"]'):
                link = file.get("href")
                media_loc = file.select_one("img").get("src").split("//i")[-1].split(".bunkr.")[0]

                if link.startswith("/"):
                    link = URL("https://" + url.host + link)
                link = URL(link)

                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue

                referer = link
                if "v" in link.parts or "d" in link.parts:
                    media = await self.get_file(session, link)
                    link = media.url
                elif ext in FILE_FORMATS["Images"]:
                    link = URL(str(link).replace("https://cdn", "https://i"))
                else:
                    link = URL(f"https://media-files{media_loc}.bunkr.ru" + link.path)

                if ext not in FILE_FORMATS['Images']:
                    link = await self.check_for_la(link)

                if self.remove_bunkr_id:
                    filename = await self.remove_id(filename, ext)

                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("bunkr", url_path)
                media = MediaItem(link, referer, complete, filename, ext, filename)
                await album.add_media(media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

        return album
