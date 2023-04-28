from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import aiofiles
from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import (
    get_filename_and_ext,
    log,
    logger,
    make_title_safe,
)
from ..base_functions.data_classes import CascadeItem, MediaItem
from ..base_functions.error_classes import FailedLoginFailure, NoExtensionFailure

if TYPE_CHECKING:
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


@dataclass
class ParseSpec:
    """Class for specific selectors of supported domains"""
    domain: str
    
    title_block_tag: str = "h1[class=p-title-value]"
    title_clutter_tag: str = field(init=False)

    posts_block_tag: str = "div[class*=message-main]"
    posts_number_tag: str = field(init=False)
    posts_number_attribute: str = "href"

    post_content_tag: str = "div[class=bbWrapper]"
    block_quote_tag: str = "blockquote"

    links_tag: str = "a"
    links_attribute: str = "href"

    images_tag: str = field(init=False)
    images_attribute: str = field(init=False)

    video_tag: str = "video source"
    video_attribute: str = "src"
    saint_iframe_tag: str = "iframe[class=saint-iframe]"
    saint_iframe_attribute: str = "src"

    embedded_content_tag: str = "span[data-s9e-mediaembed-iframe]"
    embedded_content_attribute: str = "data-s9e-mediaembed-iframe"

    attachment_block_tag: str = "section[class=message-attachments]"
    attachment_tag: str = "a"
    attachment_attribute: str = "href"

    next_page_tag: str = 'a[class="pageNav-jump pageNav-jump--next"]'
    next_page_attribute: str = "href"

    def __post_init__(self):
        if self.domain in ("simpcity", "xbunker", "socialmediagirls"):
            self.title_clutter_tag = "a" if self.domain in ("simpcity", "xbunker") else "span"
            self.posts_number_tag = "li[class=u-concealed] a"
            self.images_tag = "div[class*=bbImage]"
            self.images_attribute = "data-src"

        elif self.domain == "nudostar":
            self.title_clutter_tag = "span"
            self.posts_number_tag = "a[class=u-concealed]"
            self.images_tag = "img[class*=bbImage]"
            self.images_attribute = "src"


class ForumLogin:
    def __init__(self, name: str, username: str, password: str):
        self.name = name
        self.logged_in = False
        self.username = username
        self.password = password

    async def login(self, session: ScrapeSession, url: URL, quiet: bool):
        """Handles forum logging in"""
        if not self.username or not self.password:
            log(f"Login wasn't provided for {self.name}", quiet=quiet, style="red")
            raise FailedLoginFailure()
        attempt = 0
        while True:
            try:
                if self.logged_in:
                    return
                if attempt == 5:
                    raise FailedLoginFailure()

                assert url.host is not None
                domain = URL("https://" + url.host) / "forum/login" if "nudostar" in url.host else \
                    URL("https://" + url.host) / "login"

                text = await session.get_text(domain)
                await asyncio.sleep(5)
                soup = BeautifulSoup(text, 'html.parser')

                inputs = soup.select('form input')
                data = {
                    elem['name']: elem['value']
                    for elem in inputs
                    if elem.get('name') and elem.get('value')
                }

                assert url.host is not None
                data.update({
                    "login": self.username,
                    "password": self.password,
                    "_xfRedirect": str(URL("https://" + url.host))
                })
                await session.post_data_no_resp(domain / "login", data=data)
                await asyncio.sleep(5)
                text = await session.get_text(domain)
                if "You are already logged in" not in text:
                    raise FailedLoginFailure()

                self.logged_in = True
            except asyncio.exceptions.TimeoutError:
                attempt += 1
                continue


class XenforoCrawler:
    domains = ("nudostar", "simpcity", "socialmediagirls", "xbunker")

    def __init__(self, *, scraping_mapper, args: dict, SQL_Helper: SQLHelper, quiet: bool):
        self.include_id = args["Runtime"]["include_id"]
        self.quiet = quiet
        self.separate_posts = args["Forum_Options"]["separate_posts"]
        self.output_last = args["Forum_Options"]["output_last_forum_post"]
        self.output_last_file = args["Files"]["output_last_forum_post_file"]

        self.nudostar = ForumLogin("NudoStar",
                                   args["Authentication"]["nudostar_username"],
                                   args["Authentication"]["nudostar_password"])

        self.simpcity = ForumLogin("SimpCity",
                                   args["Authentication"]["simpcity_username"],
                                   args["Authentication"]["simpcity_password"])

        self.socialmediagirls = ForumLogin("SocialMediaGirls",
                                           args["Authentication"]["socialmediagirls_username"],
                                           args["Authentication"]["socialmediagirls_password"])

        self.xbunker = ForumLogin("XBunker",
                                  args["Authentication"]["xbunker_username"],
                                  args["Authentication"]["xbunker_password"])

        self.scraping_mapper = scraping_mapper
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL) -> tuple[CascadeItem, str]:
        """Xenforo forum director"""
        log(f"Starting: {str(url)}", quiet=self.quiet, style="green")
        cascade = CascadeItem({})

        scrape_url, post_num = await self.get_thread_url_and_post_num(url)
        title = ""
        try:
            assert url.host is not None
            if "simpcity" in url.host:
                await self.simpcity.login(session, url, self.quiet)
            elif "socialmediagirls" in url.host:
                await self.socialmediagirls.login(session, url, self.quiet)
            elif "xbunker" in url.host:
                await self.xbunker.login(session, url, self.quiet)
            elif "nudostar" in url.host:
                await self.nudostar.login(session, url, self.quiet)

            domain = next((domain for domain in self.domains if domain in url.host), None)
            if domain:
                title = await self.parse_forum(session, scrape_url, ParseSpec(domain), cascade, "", post_num)
        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            log(f"Error: {str(url)}", quiet=self.quiet, style="red")
            logger.debug(e)
            return cascade, ""

        await self.SQL_Helper.insert_cascade(cascade)
        log(f"Finished: {str(url)}", quiet=self.quiet, style="green")
        return cascade, title

    async def get_thread_url_and_post_num(self, url: URL):
        """Splits the thread url and returns the url and post number if provided"""
        post_number = 0
        if "post-" in str(url):
            post_number_parts = str(url).rsplit("post-", 1)
            post_number = int(post_number_parts[-1].strip("/")) if len(post_number_parts) == 2 else 0
            url = URL(post_number_parts[0].rstrip("#"))
        return url, post_number

    async def get_links(self, post_content, selector, attribute, domain, temp_title):
        """Grabs links from the post content based on the given selector and attribute"""
        found_links = []
        if not post_content:
            return found_links
        links = post_content.select(selector)
        for link in links:
            link = link.get(attribute)
            if link.endswith("/"):
                link = link[:-1]
            if link.startswith('//'):
                link = "https:" + link
            elif link.startswith('/'):
                link = domain / link[1:]
            found_links.append([URL(link), temp_title])
        return found_links

    async def get_embedded(self, post_content, selector, attribute, temp_title):
        """Gets embedded media from post content based on selector and attribute provided"""
        found_links = []
        links = post_content.select(selector)
        for link in links:
            embed_data = link.get(attribute)
            embed_data = embed_data.replace("\/\/", "https://www.")
            embed_data = embed_data.replace("\\", "")

            embed_url = re.search(
                r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)",
                embed_data)
            if embed_url:
                embed_url = URL(embed_url.group(0).replace("www.", ""))
                found_links.append([embed_url, temp_title])

            embed_url = re.search(
                r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\/[-a-zA-Z0-9@:%._\+~#=]*\/[-a-zA-Z0-9@:?&%._\+~#=]*",
                embed_data)
            if embed_url:
                embed_url = URL(embed_url.group(0).replace("www.", ""))
                found_links.append([embed_url, temp_title])
        return found_links

    async def filter_content_links(self, cascade: CascadeItem, content_links: list, url: URL, domain: str):
        """Splits given links into direct links and external links,
        returns external links, adds internal to the cascade"""
        assert url.host is not None
        forum_direct_urls = [x for x in content_links if x[0].host.replace(".st", ".su") in url.host]
        forum_direct_urls.extend([x for x in content_links if url.host in x[0].host.replace(".st", ".su")])
        forum_direct_urls.extend([x for x in content_links if "smgmedia" in x[0].host])
        content_links = [x for x in content_links if x not in forum_direct_urls]
        for link_title_bundle in forum_direct_urls:
            link, temp_title = link_title_bundle
            in_prog_title = temp_title + "/Attachments"
            if str(link).endswith("/"):
                link = URL(str(link)[:-1])
            if 'attachments' in link.parts or 'content' in link.parts or 'data' in link.parts:
                completed = await self.SQL_Helper.check_complete_singular(domain, link)
                try:
                    filename, ext = await get_filename_and_ext(link.name, True)
                except NoExtensionFailure:
                    continue
                media = MediaItem(link, url, completed, filename, ext, filename)
                await cascade.add_to_album(domain, in_prog_title, media)
        return content_links

    async def handle_external_links(self, content_links: list, referer: URL):
        """Maps external links to the scraper class"""
        tasks = []
        for link_title_bundle in content_links:
            link = link_title_bundle[0]
            temp_title = link_title_bundle[1]
            tasks.append(asyncio.create_task(self.scraping_mapper.map_url(link, temp_title, referer)))
        if tasks:
            await asyncio.wait(tasks)

    async def parse_forum(self, session: ScrapeSession, url: URL, spec: ParseSpec, cascade: CascadeItem,
                          title: str, post_number: int):
        """Parses forum threads"""
        soup = await session.get_BS4(url)

        assert url.host is not None
        domain = URL("https://" + url.host)
        post_num_str = ""
        content_links = []

        title_block = soup.select_one(spec.title_block_tag)
        for elem in title_block.find_all(spec.title_clutter_tag):
            elem.decompose()

        if title:
            pass
        else:
            title = title_block.text
            title = await make_title_safe(title.replace("\n", "").strip())

        posts = soup.select(spec.posts_block_tag)

        for post in posts:
            post_num_str = post.select_one(spec.posts_number_tag).get(spec.posts_number_attribute).split('/')[-1]
            post_num_int = int(post_num_str.split('post-')[-1])
            if post_number > post_num_int:
                continue

            temp_title = title + "/" + post_num_str if self.separate_posts else title

            for elem in post.find_all(spec.block_quote_tag):
                elem.decompose()
            post_content = post.select_one(spec.post_content_tag)

            # Get Links
            content_links.extend(await self.get_links(post_content, spec.links_tag, spec.links_attribute, domain,
                                                      temp_title))

            # Get Images
            content_links.extend(await self.get_links(post_content, spec.images_tag, spec.images_attribute, domain,
                                                      temp_title))

            # Get Videos:
            content_links.extend(await self.get_links(post_content, spec.video_tag, spec.video_attribute, domain,
                                                      temp_title))
            content_links.extend(await self.get_links(post_content, spec.saint_iframe_tag,
                                                      spec.saint_iframe_attribute, domain, temp_title))

            # Get Other Embedded Content
            content_links.extend(await self.get_embedded(post_content, spec.embedded_content_tag,
                                                         spec.embedded_content_attribute, temp_title))

            # Get Attachments
            attachments_block = post.select_one(spec.attachment_block_tag)
            content_links.extend(await self.get_links(attachments_block, spec.attachment_tag,
                                                      spec.attachment_attribute, domain, temp_title))

        # Handle links
        content_links = await self.filter_content_links(cascade, content_links, url, spec.domain)
        await self.handle_external_links(content_links, url)

        next_page = soup.select_one(spec.next_page_tag)
        if next_page is not None:
            next_page = next_page.get(spec.next_page_attribute)
            if next_page is not None:
                if next_page.startswith('/'):
                    next_page = domain / next_page[1:]
                next_page = URL(next_page)
                await self.parse_forum(session, next_page, spec, cascade, title, post_number)
        elif self.output_last:
            assert url.raw_name is not None
            if 'page-' in url.raw_name or 'post-' in url.raw_name:
                last_post_url = url.parent / post_num_str
            else:
                last_post_url = url / post_num_str
            async with aiofiles.open(self.output_last_file, mode='a') as f:
                await f.write(f'{last_post_url}\n')
        return title
