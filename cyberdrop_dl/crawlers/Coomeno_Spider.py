from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import CascadeItem

if TYPE_CHECKING:
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class CoomenoCrawler:
    def __init__(self, *, include_id=False, scraping_mapper, separate_posts=False, quiet: bool, SQL_Helper: SQLHelper):
        self.include_id = include_id
        self.quiet = quiet
        self.scraping_mapper = scraping_mapper
        self.separate_posts = separate_posts
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for Coomer/Kemono scraping"""
        await log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        cascade = CascadeItem({})
        title = None
        try:
            if "coomer" in url.host:
                title = await self.handle_coomer(session, url, cascade)
            elif "kemono" in url.host:
                title = await self.handle_kemono(session, url, cascade)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        await self.SQL_Helper.insert_cascade(cascade)
        await log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return cascade, title

    async def handle_coomer(self, session: ScrapeSession, url: URL, cascade: CascadeItem):
        """Coomer director function"""
        post_selectors = ['h2[class=post-card__heading] a']
        next_page_selector = 'a[title="Next page"]'
        images_selector = 'a[class="fileThumb"]'
        downloads_selector = 'a[class=post__attachment-link]'
        text_selector = 'div[class=post__content] a'

        title = "Loose Coomer Files"
        if "thumbnail" in url.parts:
            parts = [x for x in url.parts if x not in ("thumbnail", "/")]
            link = URL("https://coomer.party/" + "/".join(parts))

            media_item = await create_media_item(link, url, self.SQL_Helper, "coomer")
            await cascade.add_to_album("coomer", title, media_item)

        elif "data" in url.parts:
            media_item = await create_media_item(url, url, self.SQL_Helper, "coomer")
            await cascade.add_to_album("coomer", title, media_item)

        elif "post" in url.parts:
            title = await self.parse_post(session, url, "coomer", cascade, images_selector, downloads_selector,
                                          text_selector)

        else:
            title = await self.parse_profile(session, url, "coomer", cascade, post_selectors, next_page_selector,
                                             images_selector, downloads_selector, text_selector)

        return title

    async def handle_kemono(self, session: ScrapeSession, url: URL, cascade: CascadeItem):
        """Kemono director function"""
        post_selectors = ['article[class="post-card post-card--preview"] a', 'article[class="post-card"] a']
        next_page_selector = 'a[class=next]'
        images_selector = 'a[class="fileThumb"]'
        downloads_selector = 'a[class=post__attachment-link]'
        text_selector = 'div[class=post__content] a'

        title = "Loose Kemono Files"
        if "thumbnail" in url.parts:
            parts = [x for x in url.parts if x not in ("thumbnail", "/")]
            link = URL("https://kemono.party/" + "/".join(parts))

            media_item = await create_media_item(link, url, self.SQL_Helper, "kemono")
            await cascade.add_to_album("kemono", title, media_item)

        elif "data" in url.parts:
            media_item = await create_media_item(url, url, self.SQL_Helper, "kemono")
            await cascade.add_to_album("kemono", title, media_item)

        elif "post" in url.parts:
            title = await self.parse_post(session, url, "kemono", cascade, images_selector, downloads_selector,
                                          text_selector)

        else:
            title = await self.parse_profile(session, url, "kemono", cascade, post_selectors, next_page_selector,
                                             images_selector, downloads_selector, text_selector)

        return title

    async def map_links(self, text_content: list, title: str, referer: URL):
        """Maps external links to other scrapers"""
        tasks = []
        for content in text_content:
            link = URL(content.get('href'))
            tasks.append(asyncio.create_task(self.scraping_mapper.map_url(link, title, referer)))
        if tasks:
            await asyncio.wait(tasks)

    async def parse_profile(self, session: ScrapeSession, url: URL, domain: str, cascade: CascadeItem,
                            posts_selectors: list, next_page_selector: str, images_selector: str,
                            downloads_selector: str, text_selector: str):
        """Parses profiles with supplied selectors"""
        title = None
        try:
            soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("span[itemprop=name]").get_text())
            title = f"{title} ({url.host})"

            posts = []
            for posts_selector in posts_selectors:
                posts += soup.select(posts_selector)
            for post in posts:
                path = post.get('href')
                if path:
                    post_link = URL("https://" + url.host + path)
                    await self.parse_post(session, post_link, domain, cascade, images_selector, downloads_selector,
                                          text_selector, title)

            next_page = soup.select_one(next_page_selector)
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    await self.parse_profile(session, URL("https://" + url.host + next_page), domain, cascade,
                                             posts_selectors, next_page_selector, images_selector, downloads_selector,
                                             text_selector)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        return title

    async def parse_post(self, session: ScrapeSession, url: URL, domain: str, cascade: CascadeItem,
                         images_selector: str, downloads_selector: str, text_selector: str, title=None):
        """Parses posts with supplied selectors"""
        try:
            text = await self.SQL_Helper.get_blob(url)
            if not text:
                text = await session.get_text(url)
                await self.SQL_Helper.insert_blob(text, url)
            soup = BeautifulSoup(text, 'html.parser')

            if self.separate_posts:
                post_title = soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", "")
                prefix = f"{str(url.parts[-1])} - " if self.include_id else ""
                if title:
                    title = title + '/' + await make_title_safe(prefix + post_title)
                else:
                    title = await make_title_safe(prefix + post_title)
            elif not title:
                post_title = soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", "")
                title = await make_title_safe(post_title)

            images = soup.select(images_selector)
            for image in images:
                href = image.get('href')
                if href.startswith("/"):
                    link = URL("https://" + url.host + href)
                else:
                    link = URL(href)
                media_item = await create_media_item(link, url, self.SQL_Helper, domain)
                await cascade.add_to_album(domain, title, media_item)

            downloads = soup.select(downloads_selector)
            for download in downloads:
                href = download.get('href')
                if href.startswith("/"):
                    link = URL("https://" + url.host + href)
                else:
                    link = URL(href)
                media_item = await create_media_item(link, url, self.SQL_Helper, domain)
                await cascade.add_to_album(domain, title, media_item)

            text_content = soup.select(text_selector)
            await self.map_links(text_content, title, url)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)

        return title
