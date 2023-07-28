from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Tuple, Optional

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
    import bs4

    from ..base_functions.base_functions import ErrorFileWriter
    from ..base_functions.sql_helper import SQLHelper
    from ..client.client import ScrapeSession


@dataclass
class ParseSpec:
    """Class for specific selectors of supported domains"""
    domain: str

    login_path: str = field(init=False)
    login_wait: int = field(init=False)

    title_block_tag: str = "h1[class=p-title-value]"
    title_clutter_tag: str = field(init=False)

    posts_block_tag: str = "div[class*=message-main]"
    posts_number_tag: str = field(init=False)
    posts_number_attribute: str = "href"

    post_content_tag: str = "div[class=bbWrapper]"
    block_quote_tag: str = "blockquote"

    links_tag: str = "a"
    links_attribute: str = "href"

    images_tag: str = "img[class*=bbImage]"
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

    extra_images_tag: Optional[str] = field(init=False)
    extra_images_attribute: Optional[str] = field(init=False)

    next_page_tag: str = 'a[class="pageNav-jump pageNav-jump--next"]'
    next_page_attribute: str = "href"

    def __post_init__(self):
        if self.domain in ("simpcity", "nudostar", "xbunker"):
            self.login_wait = 5
        if self.domain in ("socialmediagirls"):
            self.login_wait = 15

        if self.domain in ("simpcity", "socialmediagirls", "xbunker"):
            self.login_path = "login"
            self.title_clutter_tag = "a" if self.domain in ("simpcity", "xbunker") else "span"
            self.posts_number_tag = "li[class=u-concealed] a"

        if self.domain in ("nudostar"):
            self.login_path = "forum/login"
            self.title_clutter_tag = "span"
            self.posts_number_tag = "a[class=u-concealed]"

        if self.domain in ("simpcity", "nudostar"):
            self.images_attribute = "src"
        if self.domain in ("xbunker", "socialmediagirls"):
            self.images_attribute = "data-src"

        if self.domain in ("simpcity", "nudostar", "socialmediagirls"):
            self.extra_images_tag = None
            self.extra_images_attribute = None
        if self.domain in ("xbunker"):
            self.extra_images_tag = "a[class*=js-lbImage]"
            self.extra_images_attribute = "href"


class ForumLogin:
    def __init__(self, name: str, username: str, password: str):
        self.name = name
        self.logged_in = False
        self.username = username
        self.password = password

    async def login(self, session: ScrapeSession, url: URL, spec: ParseSpec, quiet: bool) -> None:
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
                domain = URL("https://" + url.host) / spec.login_path

                text = await session.get_text(domain)
                await asyncio.sleep(spec.login_wait)
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
                await asyncio.sleep(spec.login_wait)
                text = await session.get_text(domain)
                if "You are already logged in" not in text:
                    raise FailedLoginFailure()

                self.logged_in = True
            except asyncio.exceptions.TimeoutError:
                attempt += 1
                continue


class XenforoCrawler:
    domains = {
        "nudostar": "NudoStar",
        "simpcity": "SimpCity",
        "socialmediagirls": "SocialMediaGirls",
        "xbunker": "XBunker",
    }

    def __init__(self, *, scraping_mapper, args: Dict, SQL_Helper: SQLHelper, quiet: bool,
                 error_writer: ErrorFileWriter):
        self.include_id = args["Runtime"]["include_id"]
        self.quiet = quiet

        self.scrape_single_post = args["Forum_Options"]["scrape_single_post"]
        self.separate_posts = args["Forum_Options"]["separate_posts"]
        self.output_last = args["Forum_Options"]["output_last_forum_post"]
        self.output_last_file = args["Files"]["output_last_forum_post_file"]

        auth_args = args["Authentication"]
        self.forums = {domain: ForumLogin(name,
                                          auth_args[f"{domain}_username"],
                                          auth_args[f"{domain}_password"])
                       for domain, name in self.domains.items()}

        self.scraping_mapper = scraping_mapper
        self.SQL_Helper = SQL_Helper

        self.error_writer = error_writer

    async def fetch(self, session: ScrapeSession, url: URL) -> Tuple[CascadeItem, str]:
        """Xenforo forum director"""
        log(f"Starting: {url}", quiet=self.quiet, style="green")
        cascade = CascadeItem({})

        scrape_url, post_num = await self.get_thread_url_and_post_num(url)
        title = ""
        try:
            assert url.host is not None
            domain = next((domain for domain in self.domains if domain in url.host), None)
            if domain:
                parse_spec = ParseSpec(domain)
                await self.forums[domain].login(session, url, parse_spec, self.quiet)
                title = await self.parse_forum(session, scrape_url, parse_spec, cascade, "", post_num)
        except Exception as e:
            logger.debug("Error encountered while handling %s", url, exc_info=True)
            await self.error_writer.write_errored_scrape(url, e, self.quiet)
            return cascade, ""

        await self.SQL_Helper.insert_cascade(cascade)
        log(f"Finished: {url}", quiet=self.quiet, style="green")
        return cascade, title

    async def get_thread_url_and_post_num(self, url: URL):
        """Splits the thread url and returns the url and post number if provided"""
        post_number = 0
        if "post-" in str(url):
            post_number_parts = str(url).rsplit("post-", 1)
            post_number = int(post_number_parts[-1].strip("/")) if len(post_number_parts) == 2 else 0
            url = URL(post_number_parts[0].rstrip("#"))
        return url, post_number

    async def get_links(self, post_content: bs4.Tag, selector: str, attribute: str, domain: URL) -> List[str]:
        """Grabs links from the post content based on the given selector and attribute"""
        found_links: List = []
        if not post_content:
            return found_links
        links = post_content.select(selector)
        for link_tag in links:
            link = link_tag.get(attribute)
            # test_for_img = link_tag.select_one("img")
            # if test_for_img:
            #     continue
            if not link:
                continue
            assert isinstance(link, str)
            if link.endswith("/"):
                link = link[:-1]
            if link.startswith('//'):
                link = "https:" + link
            elif link.startswith('/'):
                link = str(domain / link[1:])
            found_links.append(link)
        return found_links

    async def get_embedded(self, post_content: bs4.Tag, selector: str, attribute: str) -> List[str]:
        """Gets embedded media from post content based on selector and attribute provided"""
        found_links = []
        links = post_content.select(selector)
        for link_tag in links:
            embed_data = link_tag.get(attribute)
            assert isinstance(embed_data, str)
            embed_data = embed_data.replace("\/\/", "https://www.")
            embed_data = embed_data.replace("\\", "")

            embed = re.search(
                r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)",
                embed_data)
            if embed:
                embed_link = embed.group(0).replace("www.", "")
                found_links.append(embed_link)

            embed = re.search(
                r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\/[-a-zA-Z0-9@:%._\+~#=]*\/[-a-zA-Z0-9@:?&%._\+~#=]*",
                embed_data)
            if embed:
                embed_link = embed.group(0).replace("www.", "")
                found_links.append(embed_link)
        return found_links

    async def handle_direct_links(self, cascade: CascadeItem, content_links: List, url: URL, domain: str):
        """Adds given links to the cascade"""
        for link, title in content_links:
            if str(link).endswith("/"):
                link = URL(str(link)[:-1])
            if any(s in link.parts for s in ('attachments', 'content', 'data')):
                try:
                    filename, ext = await get_filename_and_ext(link.name, True)
                except NoExtensionFailure:
                    continue
                completed = await self.SQL_Helper.check_complete_singular(domain, link)
                media = MediaItem(link, url, completed, filename, ext, filename)
                await cascade.add_to_album(domain, f"{title}/Attachments", media)

    async def handle_external_links(self, content_links: List, referer: URL) -> None:
        """Maps external links to the scraper class"""
        tasks = [asyncio.create_task(self.scraping_mapper.map_url(link, title, referer))
                 for link, title in content_links]
        if tasks:
            await asyncio.wait(tasks)

    async def parse_forum(self, session: ScrapeSession, url: URL, spec: ParseSpec, cascade: CascadeItem,
                          title: str, post_number: int) -> str:
        """Parses forum threads"""
        soup = await session.get_BS4(url)
        continue_scrape = True

        assert url.host is not None
        domain = URL("https://" + url.host)
        post_num_str = ""
        content_links = []

        if not title:
            title_block = soup.select_one(spec.title_block_tag)
            for elem in title_block.find_all(spec.title_clutter_tag):
                elem.decompose()
            title = await make_title_safe(title_block.text.replace("\n", "").strip())

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
            links = await self.get_links(post_content, spec.links_tag, spec.links_attribute, domain)

            # Get Images
            links.extend(await self.get_links(post_content, spec.images_tag, spec.images_attribute, domain))

            # Get Videos:
            links.extend(await self.get_links(post_content, spec.video_tag, spec.video_attribute, domain))
            links.extend(await self.get_links(post_content, spec.saint_iframe_tag, spec.saint_iframe_attribute, domain))

            # Get Other Embedded Content
            links.extend(await self.get_embedded(post_content, spec.embedded_content_tag, spec.embedded_content_attribute))

            # Get Attachments
            attachments_block = post.select_one(spec.attachment_block_tag)
            links.extend(await self.get_links(attachments_block, spec.attachment_tag, spec.attachment_attribute, domain))

            # Get extras
            if spec.extra_images_tag:
                links.extend(await self.get_links(post_content, spec.extra_images_tag, spec.extra_images_attribute, domain))

            content_links.extend([(URL(link), temp_title) for link in links])

            if self.scrape_single_post:
                continue_scrape = False
                break

        # Handle links
        async def is_direct_link(url_to_check: URL) -> bool:
            host = url_to_check.host
            try:
                assert url.host is not None
                host_su = host.replace(".st", ".su")
                return host_su in url.host or url.host in host_su or "smgmedia" in host
            except AttributeError as e:
                logger.debug("Error encountered while handling %s", url_to_check, exc_info=True)
                await self.error_writer.write_errored_scrape(url_to_check, e, self.quiet)
                return False

        direct_links = [x for x in content_links if await is_direct_link(x[0])]
        external_links = [x for x in content_links if x not in direct_links]
        await self.handle_direct_links(cascade, direct_links, url, spec.domain)
        await self.handle_external_links(external_links, url)

        next_page = soup.select_one(spec.next_page_tag)
        if next_page is not None and continue_scrape:
            next_page = next_page.get(spec.next_page_attribute)
            if next_page is not None:
                if next_page.startswith('/'):
                    next_page = domain / next_page[1:]
                next_page = URL(next_page)
                await self.parse_forum(session, next_page, spec, cascade, title, post_number)
        else:
            assert url.raw_name is not None
            if 'page-' in url.raw_name or 'post-' in url.raw_name:
                last_post_url = url.parent / post_num_str
            else:
                last_post_url = url / post_num_str
            await self.error_writer.write_last_post(last_post_url)
        return title
