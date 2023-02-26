import asyncio

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, get_db_path, \
    get_filename_and_ext
from ..base_functions.data_classes import DomainItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class ShareXCrawler:
    def __init__(self, *, include_id=False, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for ShareX scraper"""
        domain_obj = DomainItem(url.host.lower(), {})

        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)

        if await check_direct(url):
            url = url.with_name(url.name.replace('.md.', '.').replace('.th.', '.'))
            url_path = await get_db_path(url)
            complete = await self.SQL_Helper.check_complete_singular("anonfiles", url_path)
            filename, ext = await get_filename_and_ext(url.name)
            media_item = MediaItem(url, url, complete, filename, ext, filename)
            await domain_obj.add_media("Loose ShareX Files", media_item)
        elif "album" in url.parts or "a" in url.parts:
            await self.parse(session=session, url=url, domain_obj=domain_obj)
        elif "albums" in url.parts:
            await self.get_albums(session, url, domain_obj)
        elif 'image' in url.parts or 'img' in url.parts or 'images' in url.parts:
            await self.get_singular(session, url, domain_obj)
        else:
            await self.parse_profile(session, url, domain_obj)

        url_path = await get_db_path(url)
        await self.SQL_Helper.insert_domain("sharex", url_path, domain_obj)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return domain_obj

    async def get_albums(self, session: ScrapeSession, url: URL, domain_obj: DomainItem):
        """Handles scraping for Albums"""
        try:
            soup = await session.get_BS4(url)
            albums = soup.select("a[class='image-container --media']")
            for album in albums:
                album_url = URL(album.get('href'))
                await self.parse(session=session, url=album_url, domain_obj=domain_obj)

            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    await self.get_albums(session, next_page, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_singular(self, session: ScrapeSession, url: URL, domain_obj: DomainItem):
        """Handles scraping for singular files"""
        await asyncio.sleep(1)
        try:
            soup = await session.get_BS4(url)
            link = URL(soup.select_one("input[id=embed-code-2]").get('value'))
            link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))

            url_path = await get_db_path(link)
            complete = await self.SQL_Helper.check_complete_singular("sharex", url_path)
            filename, ext = await get_filename_and_ext(link.name)
            media_item = MediaItem(link, url, complete, filename, ext, filename)
            await domain_obj.add_media("Loose ShareX Files", media_item)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_sub_album_links(self, session: ScrapeSession, url: URL, og_title: str, domain_obj: DomainItem):
        try:
            soup = await session.get_BS4(url)
            albums = soup.select("div[class=pad-content-listing] div")
            for album in albums:
                album_url = album.get('data-url-short')
                if album_url is not None:
                    album_url = URL(album_url)
                    await self.parse(session=session, url=album_url, og_title=og_title, domain_obj=domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def parse_profile(self, session: ScrapeSession, url: URL, domain_obj: DomainItem):
        """Handles scraping for profiles"""
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one("div[class=header] h1 strong").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())
            await self.get_list_links(session, url, title, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def get_list_links(self, session: ScrapeSession, url: URL, title: str, domain_obj: DomainItem):
        """Gets final links and adds to domain_obj"""
        try:
            soup = await session.get_BS4(url)
            if url.host == 'jpg.fish' or url.host == 'jpg.church':
                links = soup.select("a[href*=img] img")
            else:
                links = soup.select("a[href*=image] img")
            for link in links:
                link = URL(link.get('src'))
                link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))

                try:
                    filename, ext = await get_filename_and_ext(link.name)
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", str(link))
                    continue
                url_path = await get_db_path(link)
                complete = await self.SQL_Helper.check_complete_singular("sharex", url_path)
                media_item = MediaItem(link, url, complete, filename, ext, filename)
                await domain_obj.add_media(title, media_item)

            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    await self.get_list_links(session, next_page, title, domain_obj)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

    async def parse(self, *, session: ScrapeSession, url: URL, og_title=None, domain_obj: DomainItem):
        try:
            soup = await session.get_BS4(url)

            title = soup.select_one("a[data-text=album-name]").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())

            if og_title is not None:
                title = og_title + "/" + title

            try:
                sub_albums = URL(soup.select_one("a[id=tab-sub-link]").get("href"))
                await self.get_sub_album_links(session, sub_albums, title, domain_obj)
            finally:
                list_recent = URL(soup.select_one("a[id=list-most-recent-link]").get("href"))
                await self.get_list_links(session, list_recent, title, domain_obj)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
