from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, get_filename_and_ext
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class EromeCrawler:
    def __init__(self, *, include_id: bool, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        if 'a' in url.parts:
            domain_obj = await self.handle_album(session, url)
        else:
            domain_obj = await self.handle_profile(session, url)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def handle_album(self, session: ScrapeSession, url: URL):
        try:
            domain_obj = DomainItem("erome", {})
            soup = await session.get_BS4(url)
            title = soup.select_one('div[class="col-sm-12 page-content"] h1').get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            # Images
            for link in soup.select('img[class="img-front lasyload"]'):
                link = URL(link['data-src'])
                filename, ext = await get_filename_and_ext(link.name)
                complete = await self.SQL_Helper.check_complete_singular("erome", link.path)
                media = MediaItem(link, url, complete, filename, ext)
                await domain_obj.add_media(title, media)

            # Videos
            for link in soup.select('div[class=media-group] div[class=video-lg] video source'):
                link = URL(link['src'])
                filename, ext = await get_filename_and_ext(link.name)
                complete = await self.SQL_Helper.check_complete_singular("erome", link.path)
                media = MediaItem(link, url, complete, filename, ext)
                await domain_obj.add_media(title, media)

            await self.SQL_Helper.insert_domain("erome", url.path, domain_obj)
            return domain_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return domain_obj

    async def handle_profile(self, session: ScrapeSession, url: URL):
        try:
            domain_obj = DomainItem("erome", {})
            soup = await session.get_BS4(url)
            title = soup.select_one('h1[class="username"]').get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                title = title + " - " + url.name
            title = await make_title_safe(title)

            for album in soup.select("a[class=album-link]"):
                url = URL(album.get('href'))
                await domain_obj.extend(await self.handle_album(session, url))
            await domain_obj.append_title(title)
            return domain_obj

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return domain_obj
