from bs4 import BeautifulSoup

from ..base_functions import *
from ..data_classes import *


class ShareXCrawler():
    def __init__(self, *, include_id=False):
        self.include_id = include_id

    async def fetch(self, session, url):
        url_extract = tldextract.extract(str(url))
        base_domain = "{}.{}".format(url_extract.domain, url_extract.suffix)
        domain_obj = DomainItem(base_domain, {})

        log("Starting scrape of " + str(url), Fore.WHITE)
        logging.debug("Starting scrape of " + str(url))

        if "album" in url.parts or "a" in url.parts:
            results = await self.parse(url, session)
        elif "albums" in url.parts:
            results = await self.get_albums(url, session)
        elif 'image' in url.parts or 'img' in url.parts or 'images' in url.parts:
            results = await self.get_singular(url, session)
        else:
            results = await self.parse_profile(url, session)
        for result in results:
            domain_obj.add_to_album(result['title'], result['url'], result['referral'])

        log("Finished scrape of " + str(url), Fore.WHITE)
        logging.debug("Finished scrape of " + str(url))

        return domain_obj

    async def get_albums(self, url, session):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                albums = soup.select("a[class='image-container --media']")
                for album in albums:
                    album_url = URL(album.get('href'))
                    results.extend(result for result in await self.parse(album_url, session))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results

    async def get_singular(self, url, session):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                link = URL(soup.select_one("input[id=embed-code-2]").get('value'))
                link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
                title = "ShareX Loose Files"
                results.append({'url': link, 'title': title, 'referral': url, 'cookies': ''})
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results

    async def get_sub_album_links(self, url, session, og_title):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                albums = soup.select("div[class=pad-content-listing] div")
                for album in albums:
                    album_url = album.get('data-url-short')
                    if album_url is not None:
                        album_url = URL(album_url)
                        results.extend(result for result in await self.parse(album_url, session, og_title=og_title))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results

    async def parse_profile(self, url, session):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                title = soup.select_one("div[class=header] h1 strong").get_text()
                if title is None:
                    title = url.name
                elif self.include_id:
                    titlep2 = url.name
                    title = title + " - " + titlep2
                title = make_title_safe(title.replace(r"\n", "").strip())

                list_recent = URL(soup.select_one("a[id=list-most-recent-link]").get('href'))
                results.extend(result for result in await self.get_list_links(list_recent, session, title))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results

    async def get_list_links(self, url, session, title):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                if url.host == 'jpg.church':
                    links = soup.select("a[href*=img] img")
                else:
                    links = soup.select("a[href*=image] img")
                for link in links:
                    link = URL(link.get('src'))
                    link = link.with_name(link.name.replace('.md.', '.').replace('.th.', '.'))
                    results.append({'url': link, 'title': title, 'referral': url, 'cookies': ''})
                next_page = soup.select_one('li.pagination-next a')
                if next_page is not None:
                    next_page = next_page.get('href')
                    if next_page is not None:
                        next_page = URL(next_page)
                        results.extend(result for result in await self.get_list_links(next_page, session, title))
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results

    async def parse(self, url, session, og_title=None):
        results = []
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                title = soup.select_one("a[data-text=album-name]").get_text()
                if title is None:
                    title = url.name
                elif self.include_id:
                    titlep2 = url.name
                    title = title + " - " + titlep2
                title = make_title_safe(title.replace(r"\n", "").strip())

                if og_title is not None:
                    title = og_title + "/" + title

                sub_albums = URL(soup.select_one("a[id=tab-sub-link]").get("href"))
                results.extend(result for result in await self.get_sub_album_links(sub_albums, session, title))

                list_recent = URL(soup.select_one("a[id=list-most-recent-link]").get("href"))
                results.extend(result for result in await self.get_list_links(list_recent, session, title))

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
        return results