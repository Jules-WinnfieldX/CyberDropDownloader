from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union, List

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import CascadeItem

if TYPE_CHECKING:
    from bs4 import Tag

    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


@dataclass
class ParseSpec:
    """Class for specific selectors of supported domains"""
    domain: str
    posts_selectors: List[str] = field(init=False)
    next_page_selector: str = field(init=False)

    def __post_init__(self):
        if self.domain == "coomer":
            self.posts_selectors = ['article[class=post-card ] a']
            self.next_page_selector = 'a[class="next"]'
        elif self.domain == "kemono":
            self.posts_selectors = ['article[class="post-card post-card--preview"] a', 'article[class="post-card"] a']
            self.next_page_selector = 'a[class=next]'


class CoomenoCrawler:
    def __init__(self, *, include_id=False, scraping_mapper, separate_posts=False, skip_coomer_ads: bool, quiet: bool,
                 SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.include_id = include_id
        self.quiet = quiet
        self.scraping_mapper = scraping_mapper
        self.skip_coomer_ads = skip_coomer_ads
        self.separate_posts = separate_posts
        self.SQL_Helper = SQL_Helper
        self.limiter = AsyncLimiter(15, 1)

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL):
        """Director for Coomer/Kemono scraping"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")
        cascade = CascadeItem({})
        title = None
        try:
            assert url.host is not None
            domain = next((domain for domain in ("coomer", "kemono") if domain in url.host), None)
            if domain:
                title = await self.handle_coomeno(session, url, domain, cascade)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        await self.SQL_Helper.insert_cascade(cascade)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return cascade, title

    async def handle_coomeno(self, session: ScrapeSession, url: URL, domain: str, cascade: CascadeItem) -> str:
        """Coomer/Kemono director function"""
        title = f"Loose {domain.capitalize()} Files"
        if "thumbnail" in url.parts:
            parts = [x for x in url.parts if x not in ("thumbnail", "/")]
            link = URL(f"https://{url.host}/{'/'.join(parts)}")

            media_item = await create_media_item(link, url, self.SQL_Helper, domain)
            await cascade.add_to_album(domain, title, media_item)

        elif "data" in url.parts:
            media_item = await create_media_item(url, url, self.SQL_Helper, domain)
            await cascade.add_to_album(domain, title, media_item)

        elif "post" in url.parts:
            title = await self.parse_post(session, url, domain, cascade)

        else:
            title = await self.parse_profile(session, url, ParseSpec(domain), cascade)

        return title

    async def map_links(self, text_content: List, title: str, referer: URL):
        """Maps external links to other scrapers"""
        tasks = []
        for content in text_content:
            link = URL(content.get('href'))
            tasks.append(asyncio.create_task(self.scraping_mapper.map_url(link, title, referer)))
        if tasks:
            await asyncio.wait(tasks)

    async def parse_profile(self, session: ScrapeSession, url: URL, spec: ParseSpec, cascade: CascadeItem) -> str:
        """Parses profiles with supplied selectors"""
        title = ""
        try:
            async with self.limiter:
                soup = await session.get_BS4(url)
            title = await make_title_safe(soup.select_one("span[itemprop=name]").get_text())
            title = f"{title} ({url.host})"

            posts = []
            assert url.host is not None
            for posts_selector in spec.posts_selectors:
                posts += soup.select(posts_selector)
            for post in posts:
                path = post.get('href')
                if path:
                    post_link = URL("https://" + url.host + path)
                    await self.parse_post(session, post_link, spec.domain, cascade, title)

            next_page = soup.select_one(spec.next_page_selector)
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    await self.parse_profile(session, URL("https://" + url.host + next_page), spec, cascade)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return title

    async def parse_post(self, session: ScrapeSession, url: URL, domain: str, cascade: CascadeItem,
                         title: str = "") -> str:
        """Parses posts with supplied selectors"""
        try:
            text = await self.SQL_Helper.get_blob(url)
            if not text:
                async with self.limiter:
                    text = await session.get_text(url)
                assert text is not None
                await self.SQL_Helper.insert_blob(text, url)
            soup = BeautifulSoup(text, 'html.parser')

            if self.separate_posts:
                time_tag = soup.select_one("time[class*=timestamp]")
                post_tag = soup.select_one("h1[class=post__title]")
                assert post_tag is not None
                assert time_tag is not None
                post_title = post_tag.text.replace('\n', '').replace("..", "")
                time = time_tag.text + " - "
                prefix = f"{url.parts[-1]} - " if self.include_id else ""
                if title:
                    title = title + '/' + await make_title_safe(prefix + time + post_title)
                else:
                    title = await make_title_safe(prefix + time + post_title)
            elif not title:
                post_tag = soup.select_one("h1[class=post__title]")
                assert post_tag is not None
                post_title = post_tag.text.replace('\n', '').replace("..", "")
                title = await make_title_safe(post_title)

            text_block = soup.select_one('div[class=post__content]')
            if text_block:
                if "#AD" in text_block.text and self.skip_coomer_ads:
                    return title

            images = soup.select('a[class="fileThumb"]')
            for image in images:
                await self.parse_tag(image, url, domain, title, cascade)

            downloads = soup.select('a[class=post__attachment-link]')
            for download in downloads:
                await self.parse_tag(download, url, domain, title, cascade)

            text_content = soup.select('div[class=post__content] a')
            await self.map_links(text_content, title, url)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

        return title

    async def parse_tag(self, tag: Tag, url: URL, domain: str, title: str, cascade: CascadeItem):
        """Convert link from tag to MediaItem and add it to cascade"""
        href: Union[str, List[str], None] = tag.get('href')

        assert url.host is not None and isinstance(href, str)
        if href.startswith("/"):
            href = "https://" + url.host + href
        link = URL(href)
        media_item = await create_media_item(link, url, self.SQL_Helper, domain)
        await cascade.add_to_album(domain, title, media_item)
