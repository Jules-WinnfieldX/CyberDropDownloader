from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, List

from yarl import URL

from ..base_functions.base_functions import create_media_item, log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..base_functions.error_classes import NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


class NSFWXXXCrawler:
    def __init__(self, quiet: bool, separate_posts: bool, SQL_Helper: SQLHelper, error_writer: ErrorFileWriter):
        self.quiet = quiet
        self.separate_posts = separate_posts
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> DomainItem:
        """Director for NSFW.XXX scraping"""
        domain_obj = DomainItem("nsfw.xxx", {})

        log(f"Starting: {url}", quiet=self.quiet, style="green")
        if "user" in url.parts:
            await self.get_user(session, url, domain_obj)
        else:
            await self.get_post(session, url, domain_obj)
        await self.SQL_Helper.insert_domain("nsfw.xxx", url, domain_obj)
        return domain_obj

    async def get_user(self, session: ScrapeSession, url: URL, domain_obj: DomainItem) -> None:
        """Gets posts for a user profile"""
        if str(url).endswith("/"):
            url = url.parent

        try:
            model = url.name + " (NSFW.XXX)"
            for page in itertools.count(1):
                model_name_parts = url.path.split("/")
                model_name = list(filter(None, model_name_parts))[-1]
                page_url = URL(f"https://nsfw.xxx/page/{page}?nsfw[]=0&types[]=image&types[]=video&types[]=gallery&slider=1&jsload=1&user={model_name}")
                page_soup = await session.get_BS4(page_url)

                posts = page_soup.select('div[class="sh-section__image grid-item"] a[class=slider_init_href]')
                posts.extend(page_soup.select('div[class="sh-video__player"] a[class=slider_init_href]'))
                posts.extend(page_soup.select('div[class="sh-section__images row"] div a'))

                if not posts:
                    break

                posts = await self.get_post_hrefs(posts)
                for post in posts:
                    await self.get_post(session, post, domain_obj, model)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)

    async def get_post_hrefs(self, posts) -> List:
        """Gets links from post objects"""
        posts_links = []
        for post in posts:
            url = URL(post.get("href"))
            if url not in posts_links:
                posts_links.append(url)
        return posts_links

    async def get_post(self, session: ScrapeSession, url: URL, domain_obj: DomainItem, model=None) -> None:
        """Gets content for a given post url"""
        try:
            soup = await session.get_BS4(url)
            if not model:
                model = await make_title_safe(soup.select_one("a[class=sh-section__name]").get_text()) + " (NSFW.XXX)"
            post_name = await make_title_safe(soup.select_one("div[class=sh-section__content] p").get_text())

            content_obj = soup.select("div[class=sh-section__image] img")
            content_obj.extend(soup.select("video source"))
            content_obj.extend(soup.select('div[class="sh-section__images sh-section__images_gallery row"] div a img'))

            for content in content_obj:
                link = URL(content.get("src"))
                if "-mobile" in link.name or ".webm" in link.name:
                    continue
                try:
                    media = await create_media_item(link, url, self.SQL_Helper, "nsfw.xxx")
                except NoExtensionFailure:
                    logger.debug("Couldn't get extension for %s", link)
                    continue

                title = f"{model}/{post_name}" if self.separate_posts else model
                await domain_obj.add_media(title, media)

        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
