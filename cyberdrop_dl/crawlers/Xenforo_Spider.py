from __future__ import annotations

import asyncio
import re

from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import log, make_title_safe, write_last_post_file, get_filename_and_ext, logger
from ..base_functions.data_classes import CascadeItem, MediaItem
from ..base_functions.error_classes import FailedLoginFailure, NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class XenforoCrawler:
    def __init__(self, *, scraping_mapper, args: dict, SQL_Helper: SQLHelper, quiet: bool):
        self.include_id = args["Runtime"]["include_id"]
        self.quiet = quiet
        self.separate_posts = args["Forum_Options"]["separate_posts"]
        self.output_last = args["Forum_Options"]["output_last_forum_post"]
        self.output_last_file = args["Files"]["output_last_forum_post_file"]

        self.simpcity_logged_in = False
        self.simpcity_lock = False
        self.simpcity_username = args["Authentication"]["simpcity_username"]
        self.simpcity_password = args["Authentication"]["simpcity_password"]

        self.socialmediagirls_logged_in = False
        self.socialmediagirls_lock = False
        self.socialmediagirls_username = args["Authentication"]["socialmediagirls_username"]
        self.socialmediagirls_password = args["Authentication"]["socialmediagirls_password"]

        self.xbunker_logged_in = False
        self.xbunker_lock = False
        self.xbunker_username = args["Authentication"]["xbunker_username"]
        self.xbunker_password = args["Authentication"]["xbunker_password"]

        self.scraping_mapper = scraping_mapper
        self.SQL_Helper = SQL_Helper

    async def fetch(self, session: ScrapeSession, url: URL):
        """Xenforo forum director"""
        await log(f"[green]Starting: {str(url)}[/green]", quiet=self.quiet)
        cascade = CascadeItem({})

        scrape_url, post_num = await self.get_thread_url_and_post_num(url)
        title = None
        try:
            if "simpcity" in url.host:
                await self.simpcity_login(session, url)
                title = await self.parse_simpcity(session, scrape_url, cascade, "", post_num)
            elif "socialmediagirls" in url.host:
                await self.socialmediagirls_login(session, url)
                title = await self.parse_socialmediagirls(session, scrape_url, cascade, "", post_num)
            elif "xbunker" in url.host:
                await self.xbunker_login(session, url)
                title = await self.parse_xbunker(session, scrape_url, cascade, "", post_num)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return cascade, ""

        await self.SQL_Helper.insert_cascade(cascade)
        await log(f"[green]Finished: {str(url)}[/green]", quiet=self.quiet)
        return cascade, title

    async def simpcity_login(self, session: ScrapeSession, url: URL):
        """Handles logging in for simpcity"""
        if self.simpcity_username and self.simpcity_username:
            if not self.simpcity_lock:
                while True:
                    if self.simpcity_logged_in:
                        return
                    self.simpcity_lock = True
                    domain = URL("https://" + url.host) / "login"
                    text = await session.get_text(domain)
                    soup = BeautifulSoup(text, 'html.parser')

                    inputs = soup.select('form input')
                    data = {
                        elem['name']: elem['value']
                        for elem in inputs
                        if elem.get('name') and elem.get('value')
                    }
                    data.update({"login": self.simpcity_username, "password": self.simpcity_password,
                                 "_xfRedirect": str(domain)})
                    await session.post_data_no_resp(domain / "login", data=data)
                    text = await session.get_text(domain)
                    if "You are already logged in" in text:
                        self.simpcity_logged_in = True
                        self.simpcity_lock = False
                        return
                    else:
                        self.simpcity_lock = False
                        raise FailedLoginFailure()
        else:
            await log("[red]Login wasn't provided for SimpCity[/red]", quiet=self.quiet)
            raise FailedLoginFailure()

    async def socialmediagirls_login(self, session: ScrapeSession, url: URL):
        """Handles logging in for SMG"""
        if self.socialmediagirls_username and self.socialmediagirls_username:
            if not self.socialmediagirls_lock:
                while True:
                    if self.socialmediagirls_logged_in:
                        return
                    self.socialmediagirls_lock = True
                    domain = URL("https://" + url.host) / "login"
                    text = await session.get_text(domain)
                    soup = BeautifulSoup(text, 'html.parser')

                    inputs = soup.select('form input')
                    data = {
                        elem['name']: elem['value']
                        for elem in inputs
                        if elem.get('name') and elem.get('value')
                    }
                    data.update({"login": self.socialmediagirls_username, "password": self.socialmediagirls_password,
                                 "_xfRedirect": str(domain)})
                    await session.post_data_no_resp(domain / "login", data=data)
                    text = await session.get_text(domain)
                    if "You are already logged in" in text:
                        self.socialmediagirls_logged_in = True
                        self.socialmediagirls_lock = False
                        return
                    else:
                        self.socialmediagirls_lock = False
                        raise FailedLoginFailure()
        else:
            await log("[red]Login wasn't provided for SocialMediaGirls[/red]", quiet=self.quiet)
            raise FailedLoginFailure()

    async def xbunker_login(self, session: ScrapeSession, url: URL):
        """Handles logging in for XBunker"""
        if self.xbunker_username and self.xbunker_password:
            if not self.xbunker_lock:
                while True:
                    if self.xbunker_logged_in:
                        return
                    self.xbunker_lock = True
                    domain = URL("https://" + url.host) / "login"
                    text = await session.get_text(domain)
                    soup = BeautifulSoup(text, 'html.parser')

                    inputs = soup.select('form input')
                    data = {
                        elem['name']: elem['value']
                        for elem in inputs
                        if elem.get('name') and elem.get('value')
                    }
                    data.update({"login": self.xbunker_username, "password": self.xbunker_password,
                                 "_xfRedirect": str(domain)})
                    await session.post_data_no_resp(domain / "login", data=data)
                    text = await session.get_text(domain)
                    if "You are already logged in" in text:
                        self.xbunker_logged_in = True
                        self.xbunker_lock = False
                        return
                    else:
                        self.xbunker_lock = False
                        raise FailedLoginFailure()
        else:
            await log("[red]Login wasn't provided for SocialMediaGirls[/red]", quiet=self.quiet)
            raise FailedLoginFailure()

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

    async def get_embedded(self, post_content, selector, attribute, domain, temp_title):
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
        forum_direct_urls = [x for x in content_links if x[0].host.replace(".st", ".su") in url.host]
        forum_direct_urls.extend([x for x in content_links if url.host in x[0].host.replace(".st", ".su")])
        content_links = [x for x in content_links if x not in forum_direct_urls]
        for link_title_bundle in forum_direct_urls:
            link = link_title_bundle[0]
            temp_title = link_title_bundle[1]
            in_prog_title = temp_title + "/Attachments"
            if str(link).endswith("/"):
                link = URL(str(link)[:-1])
            if 'attachments' in link.parts or 'content' in link.parts or 'data' in link.parts:
                completed = await self.SQL_Helper.check_complete_singular(domain, link.path)
                try:
                    filename, ext = await get_filename_and_ext(link.name, True)
                except NoExtensionFailure:
                    continue
                media = MediaItem(link, url, completed, filename, ext)
                await cascade.add_to_album(domain, in_prog_title, media)
        return content_links

    async def handle_external_links(self, content_links: list, referer: URL):
        """Maps external links to the scraper class"""
        tasks = []
        for link_title_bundle in content_links:
            link = link_title_bundle[0]
            temp_title = link_title_bundle[1]
            tasks.append(self.scraping_mapper.map_url(link, temp_title, referer))
        if tasks:
            await asyncio.wait(tasks)

    async def parse_simpcity(self, session: ScrapeSession, url: URL, cascade: CascadeItem, title: str,
                             post_number: int):
        """Parses simpcity threads"""
        soup = await session.get_BS4(url)

        domain = URL("https://" + url.host)
        post_num_str = None
        content_links = []

        title_block = soup.select_one("h1[class=p-title-value]")
        for elem in title_block.find_all("a"):
            elem.decompose()

        if title:
            pass
        else:
            title = title_block.text
            title = await make_title_safe(title.replace("\n", "").strip())

        posts = soup.select("div[class='message-main uix_messageContent js-quickEditTarget']")

        for post in posts:
            post_num_str = post.select_one("li[class=u-concealed] a").get('href').split('/')[-1]
            post_num_int = int(post_num_str.split('post-')[-1])
            if post_number:
                if post_number > post_num_int:
                    continue

            temp_title = title + "/" + post_num_str if self.separate_posts else title

            for elem in post.find_all('blockquote'):
                elem.decompose()
            post_content = post.select_one("div[class=bbWrapper]")

            # Get Links
            content_links.extend(await self.get_links(post_content, "a", "href", domain, temp_title))

            # Get Images
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper js-lbImage']", "data-src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper lazyload js-lbImage']", "data-src", domain, temp_title))

            # Get Videos:
            content_links.extend(await self.get_links(post_content, "video source", "src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "iframe[class=saint-iframe]", "src", domain, temp_title))

            # Get Other Embedded Content
            content_links.extend(await self.get_embedded(post_content, "span[data-s9e-mediaembed-iframe]", "data-s9e-mediaembed-iframe",
                                 domain, temp_title))

            # Get Attachments
            attachments_block = post.select_one("section[class=message-attachments]")
            content_links.extend(await self.get_links(post_content, "a[class='file-preview js-lbImage']", "href", domain, temp_title))

        # Handle links
        content_links = await self.filter_content_links(cascade, content_links, url, "simpcity")
        await self.handle_external_links(content_links, url)

        next_page = soup.select_one('a[class="pageNav-jump pageNav-jump--next"]')
        if next_page is not None:
            next_page = next_page.get('href')
            if next_page is not None:
                if next_page.startswith('/'):
                    next_page = domain / next_page[1:]
                next_page = URL(next_page)
                await self.parse_simpcity(session, next_page, cascade, title, post_number)
        else:
            if self.output_last:
                if 'page-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                elif 'post-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                else:
                    last_post_url = url / post_num_str
                await write_last_post_file(self.output_last_file, str(last_post_url))
        return title

    async def parse_socialmediagirls(self, session: ScrapeSession, url: URL, cascade: CascadeItem, title: str,
                                     post_number: int):
        """Parses SMG threads"""
        soup = await session.get_BS4(url)

        domain = URL("https://" + url.host)
        post_num_str = None
        content_links = []

        title_block = soup.select_one("h1[class=p-title-value]")
        for elem in title_block.find_all("a"):
            elem.decompose()

        if title:
            pass
        else:
            title = title_block.text
            title = await make_title_safe(title.replace("\n", "").strip())

        posts = soup.select("div[class='message-main uix_messageContent js-quickEditTarget']")

        for post in posts:
            post_num_str = post.select_one("li[class=u-concealed] a").get('href').split('/')[-1]
            post_num_int = int(post_num_str.split('post-')[-1])
            if post_number:
                if post_number > post_num_int:
                    continue

            temp_title = title + "/" + post_num_str if self.separate_posts else title

            for elem in post.find_all('blockquote'):
                elem.decompose()
            post_content = post.select_one("div[class=bbWrapper]")

            # Get Links
            content_links.extend(await self.get_links(post_content, "a", "href", domain, temp_title))

            # Get Images
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper js-lbImage']", "data-src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper lazyload js-lbImage']", "data-src", domain, temp_title))

            # Get Videos:
            content_links.extend(await self.get_links(post_content, "video source", "src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "iframe[class=saint-iframe]", "src", domain, temp_title))

            # Get Other Embedded Content
            content_links.extend(await self.get_embedded(post_content, "span[data-s9e-mediaembed-iframe]", "data-s9e-mediaembed-iframe", domain, temp_title))

            # Get Attachments
            attachments_block = post.select_one("section[class=message-attachments]")
            content_links.extend(await self.get_links(post_content, "a[class='file-preview js-lbImage']", "href", domain, temp_title))

        # Handle links
        content_links = await self.filter_content_links(cascade, content_links, url, "socialmediagirls")
        await self.handle_external_links(content_links, url)

        next_page = soup.select_one('a[class="pageNav-jump pageNav-jump--next"]')
        if next_page is not None:
            next_page = next_page.get('href')
            if next_page is not None:
                if next_page.startswith('/'):
                    next_page = domain / next_page[1:]
                next_page = URL(next_page)
                await self.parse_socialmediagirls(session, next_page, cascade, title, post_number)
        else:
            if self.output_last:
                if 'page-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                elif 'post-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                else:
                    last_post_url = url / post_num_str
                await write_last_post_file(self.output_last_file, str(last_post_url))
        return title

    async def parse_xbunker(self, session: ScrapeSession, url: URL, cascade: CascadeItem, title: str,
                            post_number: int):
        """Parses XBunker threads"""
        soup = await session.get_BS4(url)

        domain = URL("https://" + url.host)
        post_num_str = None
        content_links = []

        title_block = soup.select_one("h1[class=p-title-value]")
        for elem in title_block.find_all("a"):
            elem.decompose()

        if title:
            pass
        else:
            title = title_block.text
            title = await make_title_safe(title.replace("\n", "").strip())

        posts = soup.select("div[class='message-main uix_messageContent js-quickEditTarget']")

        for post in posts:
            post_num_str = post.select_one("li[class=u-concealed] a").get('href').split('/')[-1]
            post_num_int = int(post_num_str.split('post-')[-1])
            if post_number:
                if post_number > post_num_int:
                    continue

            temp_title = title + "/" + post_num_str if self.separate_posts else title

            for elem in post.find_all('blockquote'):
                elem.decompose()
            post_content = post.select_one("div[class=bbWrapper]")

            # Get Links
            content_links.extend(await self.get_links(post_content, "a", "href", domain, temp_title))

            # Get Images
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper js-lbImage']", "data-src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "div[class='bbImageWrapper lazyload js-lbImage']", "data-src", domain, temp_title))

            # Get Videos:
            content_links.extend(await self.get_links(post_content, "video source", "src", domain, temp_title))
            content_links.extend(await self.get_links(post_content, "iframe[class=saint-iframe]", "src", domain, temp_title))

            # Get Other Embedded Content
            content_links.extend(await self.get_embedded(post_content, "span[data-s9e-mediaembed-iframe]", "data-s9e-mediaembed-iframe", domain, temp_title))

            # Get Attachments
            attachments_block = post.select_one("section[class=message-attachments]")
            content_links.extend(await self.get_links(post_content, "a[class='file-preview js-lbImage']", "href", domain, temp_title))

        # Handle links
        content_links = await self.filter_content_links(cascade, content_links, url, "xbunker")
        await self.handle_external_links(content_links, url)

        next_page = soup.select_one('a[class="pageNav-jump pageNav-jump--next"]')
        if next_page is not None:
            next_page = next_page.get('href')
            if next_page is not None:
                if next_page.startswith('/'):
                    next_page = domain / next_page[1:]
                next_page = URL(next_page)
                await self.parse_xbunker(session, next_page, cascade, title, post_number)
        else:
            if self.output_last:
                if 'page-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                elif 'post-' in url.raw_name:
                    last_post_url = url.parent / post_num_str
                else:
                    last_post_url = url / post_num_str
                await write_last_post_file(self.output_last_file, str(last_post_url))
        return title
