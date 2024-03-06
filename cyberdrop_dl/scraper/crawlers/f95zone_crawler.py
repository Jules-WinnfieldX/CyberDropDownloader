from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from aiolimiter import AsyncLimiter
from bs4 import Tag
from yarl import URL

from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import get_filename_and_ext, error_handling_wrapper, log

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class F95ZoneCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "f95zone", "F95Zone")
        self.primary_base_domain = URL("https://f95zone.to")
        self.logged_in = False
        self.request_limiter = AsyncLimiter(10, 1)

        self.title_selector = "h1[class=p-title-value]"
        self.title_trash_selector = "a"
        self.posts_selector = "div[class*=message-main]"
        self.post_date_selector = "time"
        self.post_date_attribute = "data-time"
        self.posts_number_selector = "a[class=u-concealed]"
        self.posts_number_attribute = "href"
        self.quotes_selector = "blockquote"
        self.posts_content_selector = "div[class*=message-content]"
        self.next_page_selector = "a[class*=pageNav-jump--next]"
        self.next_page_attribute = "href"
        self.links_selector = "a"
        self.links_attribute = "href"
        self.attachment_url_part = "attachments"
        self.images_selector = "img[class*=bbImage]"
        self.images_attribute = "data-src"
        self.videos_selector = "video source"
        self.iframe_selector = "iframe[class=saint-iframe]"
        self.videos_attribute = "src"
        self.embeds_selector = "iframe"
        self.embeds_attribute = "src"
        self.attachments_block_selector = "section[class=message-attachments]"
        self.attachments_selector = "a"
        self.attachments_attribute = "href"

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if not self.logged_in:
            login_url = self.primary_base_domain / "login"
            session_cookie = self.manager.config_manager.authentication_data['Forums']['f95zone_xf_user_cookie']
            username = self.manager.config_manager.authentication_data['Forums']['f95zone_username']
            password = self.manager.config_manager.authentication_data['Forums']['f95zone_password']
            wait_time = 5

            await self.forum_login(login_url, session_cookie, username, password, wait_time)

        if self.logged_in:
            await self.forum(scrape_item)
        else:
            await log("F95Zone login failed. Skipping.", 40)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def forum(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        continue_scraping = True

        thread_url = scrape_item.url
        post_number = 0
        if len(scrape_item.url.parts) > 3:
            if "post-" in str(scrape_item.url.parts[3]) or "post-" in scrape_item.url.fragment:
                url_parts = str(scrape_item.url).rsplit("post-", 1)
                thread_url = URL(url_parts[0].rstrip("#"))
                post_number = int(url_parts[-1].strip("/")) if len(url_parts) == 2 else 0

        current_post_number = 0
        while True:
            async with self.request_limiter:
                soup = await self.client.get_BS4(self.domain, thread_url)

            title_block = soup.select_one(self.title_selector)
            for elem in title_block.find_all(self.title_trash_selector):
                elem.decompose()

            thread_id = thread_url.parts[2].split('.')[-1]
            title = await self.create_title(title_block.text.replace("\n", ""), None, thread_id)

            posts = soup.select(self.posts_selector)
            for post in posts:
                current_post_number = int(post.select_one(self.posts_number_selector).get(self.posts_number_attribute).split('/')[-1].split('post-')[-1])
                scrape_post, continue_scraping = await self.check_post_number(post_number, current_post_number)

                if scrape_post:
                    date = int(post.select_one(self.post_date_selector).get(self.post_date_attribute))
                    new_scrape_item = await self.create_scrape_item(scrape_item, thread_url, title, False, None, date)

                    for elem in post.find_all(self.quotes_selector):
                        elem.decompose()
                    post_content = post.select_one(self.posts_content_selector)
                    await self.post(new_scrape_item, post_content, current_post_number)

                if not continue_scraping:
                    break

            next_page = soup.select_one(self.next_page_selector)
            if next_page and continue_scraping:
                thread_url = next_page.get(self.next_page_attribute)
                if thread_url:
                    if thread_url.startswith("/"):
                        thread_url = self.primary_base_domain / thread_url[1:]
                    thread_url = URL(thread_url)
                    continue
            else:
                break
        post_string = f"post-{current_post_number}"
        if "page-" in scrape_item.url.raw_name or "post-" in scrape_item.url.raw_name:
            last_post_url = scrape_item.url.parent / post_string
        else:
            last_post_url = scrape_item.url / post_string
        await self.manager.log_manager.write_last_post_log(last_post_url)

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem, post_content: Tag, post_number: int) -> None:
        """Scrapes a post"""
        if self.manager.config_manager.settings_data['Download_Options']['separate_posts']:
            scrape_item = await self.create_scrape_item(scrape_item, scrape_item.url, "")
            await scrape_item.add_to_parent_title("post-" + str(post_number))

        await self.links(scrape_item, post_content)
        await self.images(scrape_item, post_content)
        await self.videos(scrape_item, post_content)
        await self.embeds(scrape_item, post_content)
        await self.attachments(scrape_item, post_content)

    @error_handling_wrapper
    async def links(self, scrape_item: ScrapeItem, post_content: Tag) -> None:
        """Scrapes links from a post"""
        links = post_content.select(self.links_selector)
        for link_obj in links:
            link = link_obj.get(self.links_attribute)
            if not link:
                continue

            link = link.replace(".th.", ".").replace(".md.", ".")

            if link.endswith("/"):
                link = link[:-1]

            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = self.primary_base_domain / link[1:]
            link = URL(link)

            if "masked" in link.path:
                link = await self.handle_link_confirmation(link)
                if not link:
                    continue

            try:
                if self.domain not in link.host:
                    new_scrape_item = await self.create_scrape_item(scrape_item, link, "")
                    await self.handle_external_links(new_scrape_item)
                elif self.attachment_url_part in link.host:
                    await self.handle_internal_links(link, scrape_item)
                else:
                    await log(f"Unknown link type: {link}", 30)
                    continue
            except TypeError:
                await log(f"Scrape Failed: encountered while handling {link}", 40)

    @error_handling_wrapper
    async def images(self, scrape_item: ScrapeItem, post_content: Tag) -> None:
        """Scrapes images from a post"""
        images = post_content.select(self.images_selector)
        for image in images:
            link = image.get(self.images_attribute)
            if not link:
                continue

            parent_check = image.parent.get("href")
            if parent_check:
                continue

            link = link.replace(".th.", ".").replace(".md.", ".")
            if link.endswith("/"):
                link = link[:-1]

            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = self.primary_base_domain / link[1:]
            link = URL(link)

            if self.domain not in link.host:
                new_scrape_item = await self.create_scrape_item(scrape_item, link, "")
                await self.handle_external_links(new_scrape_item)
            elif self.attachment_url_part in link.host:
                await self.handle_internal_links(link, scrape_item)
            else:
                await log(f"Unknown image type: {link}", 30)
                continue

    @error_handling_wrapper
    async def videos(self, scrape_item: ScrapeItem, post_content: Tag) -> None:
        """Scrapes videos from a post"""
        videos = post_content.select(self.videos_selector)
        videos.extend(post_content.select(self.iframe_selector))

        for video in videos:
            link = video.get(self.videos_attribute)
            if not link:
                continue

            if link.endswith("/"):
                link = link[:-1]

            if link.startswith("//"):
                link = "https:" + link

            link = URL(link)
            new_scrape_item = await self.create_scrape_item(scrape_item, link, "")
            await self.handle_external_links(new_scrape_item)

    @error_handling_wrapper
    async def embeds(self, scrape_item: ScrapeItem, post_content: Tag) -> None:
        """Scrapes embeds from a post"""
        embeds = post_content.select(self.embeds_selector)
        for embed in embeds:
            link = embed.get(self.embeds_attribute)
            if not link:
                continue

            link = link.replace("ifr", "watch")

            link = URL(link)
            new_scrape_item = await self.create_scrape_item(scrape_item, link, "")
            await self.handle_external_links(new_scrape_item)

    @error_handling_wrapper
    async def attachments(self, scrape_item: ScrapeItem, post_content: Tag) -> None:
        """Scrapes attachments from a post"""
        attachment_block = post_content.select_one(self.attachments_block_selector)
        if not attachment_block:
            return

        attachments = attachment_block.select(self.attachments_selector)
        for attachment in attachments:
            link = attachment.get(self.attachments_attribute)
            if not link:
                continue

            if link.endswith("/"):
                link = link[:-1]

            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = self.primary_base_domain / link[1:]
            link = URL(link)

            if self.domain not in link.host:
                new_scrape_item = await self.create_scrape_item(scrape_item, link, "")
                await self.handle_external_links(new_scrape_item)
            elif self.attachment_url_part in link.host:
                await self.handle_internal_links(link, scrape_item)
            else:
                await log(f"Unknown image type: {link}", 30)
                continue

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    @error_handling_wrapper
    async def handle_internal_links(self, link: URL, scrape_item: ScrapeItem) -> None:
        """Handles internal links"""
        filename, ext = await get_filename_and_ext(link.name, True)
        new_scrape_item = await self.create_scrape_item(scrape_item, link, "Attachments", True)
        await self.handle_file(link, new_scrape_item, filename, ext)

    @error_handling_wrapper
    async def handle_link_confirmation(self, link: URL) -> Optional[URL]:
        """Handles link confirmation"""
        async with self.request_limiter:
            await self.client.get_BS4(self.domain, link)
        async with self.request_limiter:
            JSON_Resp = await self.client.post_data(self.domain, link, data={"xhr": "1", "download": "1"})

        if JSON_Resp['status'] == "ok":
            return URL(JSON_Resp['msg'])
