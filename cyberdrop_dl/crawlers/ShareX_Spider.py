import asyncio

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class ShareXCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})

        await log("Starting scrape of " + str(url), quiet=self.quiet)

        if await check_direct(url):
            url = url.with_name(url.name.replace('.md.', '.').replace('.th.', '.'))
            await domain_obj.add_to_album(link=url, referral=url, title="ShareX Loose Files")
            return domain_obj

        if "album" in url.parts or "a" in url.parts:
            results = await self.parse(session, url)
        elif "albums" in url.parts:
            results = await self.get_albums(session, url)
        elif 'image' in url.parts or 'img' in url.parts or 'images' in url.parts:
            results = await self.get_singular(session, url)
        else:
            results = await self.parse_profile(session, url)

        for result in results:
            await domain_obj.add_to_album(result['title'], result['url'], result['referral'])

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def get_albums(self, session: Session, url: URL):
        results = []
        try:
            soup = await session.get_BS4(url)
            albums = soup.select("a[class='image-container --media']")
            for album in albums:
                album_url = URL(album.get('href'))
                results.extend(result for result in await self.parse(session, album_url))

            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    results.extend(result for result in await self.get_albums(session, next_page))

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results

    async def get_singular(self, session: Session, url: URL):
        results = []
        await asyncio.sleep(1)
        try:
            soup = await session.get_BS4(url)
            link = URL(soup.select_one("input[id=embed-code-2]").get('value'))
            link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
            title = "ShareX Loose Files"
            results.append({'url': link, 'title': title, 'referral': url, 'cookies': ''})
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results

    async def get_sub_album_links(self, session: Session, url: URL, og_title: str):
        results = []
        try:
            soup = await session.get_BS4(url)
            albums = soup.select("div[class=pad-content-listing] div")
            for album in albums:
                album_url = album.get('data-url-short')
                if album_url is not None:
                    album_url = URL(album_url)
                    results.extend(result for result in await self.parse(session, album_url, og_title=og_title))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results

    async def parse_profile(self, session: Session, url: URL):
        results = []
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one("div[class=header] h1 strong").get_text()
            if title is None:
                title = url.name
            elif self.include_id:
                titlep2 = url.name
                title = title + " - " + titlep2
            title = await make_title_safe(title.replace(r"\n", "").strip())
            results.extend(result for result in await self.get_list_links(session, url, title))

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results

    async def get_list_links(self, session: Session, url: URL, title: str):
        results = []
        try:
            soup = await session.get_BS4(url)
            if url.host == 'jpg.church':
                links = soup.select("a[href*=img] img")
            else:
                links = soup.select("a[href*=image] img")
            for link in links:
                link = URL(link.get('src'))
                link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
                results.append({'url': link, 'title': title, 'referral': url, 'cookies': ''})
            next_page = soup.select_one('li.pagination-next a')
            if not next_page:
                next_page = soup.select_one('a[data-pagination=next]')
            if next_page is not None:
                next_page = next_page.get('href')
                if next_page is not None:
                    next_page = URL(next_page)
                    results.extend(result for result in await self.get_list_links(session, next_page, title))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results

    async def parse(self, session: Session, url: URL, og_title=None, page=None, prior_result=None):
        results = []
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
                results.extend(result for result in await self.get_sub_album_links(session, sub_albums, title))
            finally:
                list_recent = URL(soup.select_one("a[id=list-most-recent-link]").get("href"))
                results.extend(result for result in await self.get_list_links(session, list_recent, title))

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
        return results
