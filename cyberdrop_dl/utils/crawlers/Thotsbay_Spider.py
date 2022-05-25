import asyncio
import re

from bs4 import BeautifulSoup
from colorama import Fore
from yarl import URL

from ..base_functions import log, logger, make_title_safe, ssl_context
from ..data_classes import AuthData, CascadeItem


class ThotsbayCrawler:
    def __init__(self, *, include_id=False, auth: AuthData = None, scraping_mapper, session, separate_posts=False):
        self.include_id = include_id
        self.separate_posts = separate_posts
        self.username, self.password = (auth.username, auth.password) if auth else (None, None)
        self.scraping_mapper = scraping_mapper
        self.session = session
        self.lock = 0

    async def login(self, session, url: URL):
        domain = URL("https://" + url.host) / "login"
        async with session.get(domain, ssl=ssl_context) as response:
            text = await response.text()
            if "You are already logged in" in text:
                return
            soup = BeautifulSoup(text, 'html.parser')

            inputs = soup.select('form input')
            data = {
                elem['name']: elem['value']
                for elem in inputs
                if elem.get('name') and elem.get('value')
            }
            data.update({"login": self.username, "password": self.password})
            return await session.post(domain/"login", data=data)

    async def fetch(self, session, url: URL):
        await log("Starting scrape of " + str(url), Fore.WHITE)
        Cascade = CascadeItem({})

        try:
            if self.username and self.password:
                while True:
                    if self.lock == 0:
                        self.lock = 1
                        await self.login(session, url)
                        self.lock = 0
                        break
                    else:
                        await asyncio.sleep(2)
            else:
                await log("login wasn't provided, consider using --thotsbay-username and --thotsbay-password")
                await log("Not being logged in might cause issues.")
            await self.parse_thread(session, url, Cascade, None)
        except Exception as e:
            await log("there was an error signing into %s" % url.host)
            await log(e)
            return

        await log("Finished scrape of " + str(url), Fore.WHITE)
        return Cascade

    async def parse_thread(self, session, url, Cascade, title):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                domain = URL("https://" + url.host)

                title_block = soup.select_one("h1[class=p-title-value]")
                for elem in title_block.find_all("a"):
                    elem.decompose()

                if title:
                    pass
                else:
                    title = title_block.text
                    if self.include_id:
                        titlep2 = url.name
                        titlep2 = [s for s in titlep2 if "." in s][-1]
                        title = title + " - " + titlep2
                    title = await make_title_safe(title.replace(r"\n", "").strip())

                content_links = []

                post_number = str(url).split("post-")
                post_number = int(post_number[-1].strip("/")) if len(post_number) == 2 else None

                posts = soup.select("div[class='message-main uix_messageContent js-quickEditTarget']")
                for post in posts:
                    post_num_str = post.select_one("li[class=u-concealed] a").get('href').split('/')[-1]
                    post_num_int = int(post_num_str.split('post-')[-1])
                    if post_number:
                        if post_number > post_num_int:
                            continue

                    temp_title = title+"/"+post_num_str if self.separate_posts else title

                    for elem in post.find_all('blockquote'):
                        elem.decompose()
                    post_content = post.select_one("div[class=bbWrapper]")

                    # Content links
                    links = post_content.select('a')
                    for link in links:
                        link = link.get('href')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = domain / link[1:]
                        content_links.append([URL(link), temp_title])

                    links = post.select("div[class='bbImageWrapper js-lbImage']")
                    for link in links:
                        link = link.get('data-src')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('/'):
                            link = domain / link[1:]
                        content_links.append([URL(link), temp_title])

                    links = post.select("div[class='bbImageWrapper lazyload js-lbImage']")
                    for link in links:
                        link = link.get('data-src')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = domain / link[1:]
                        content_links.append([URL(link), temp_title])

                    links = post.select("video source")
                    for link in links:
                        link = link.get('src')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = domain / link[1:]
                        content_links.append([URL(link), temp_title])

                    links = post.select('iframe[class=saint-iframe]')
                    for link in links:
                        link = link.get('src')
                        content_links.append([URL(link), temp_title])

                    attachments_block = post.select_one("section[class=message-attachments]")
                    links = attachments_block.select("a[class='file-preview js-lbImage']") if attachments_block else []
                    for link in links:
                        link = link.get('href')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('/'):
                            link = domain / link[1:]
                        in_prog_title = temp_title + "/Attachments"
                        await Cascade.add_to_album(url.host, in_prog_title, URL(link), url)

                    # Gyfcat / Redgifs / Imgur
                    # NOTE IMGUR SUPPORT IS NOT WORKING AS OF NOW
                    links = post_content.select("span[data-s9e-mediaembed-iframe]")
                    for link in links:
                        embed_data = link.get("data-s9e-mediaembed-iframe")
                        # Replace gyfcat/redgifs/imgur embed url escape chars
                        embed_data = embed_data.replace("\/\/", "https://www.")
                        embed_data = embed_data.replace("\\", "")

                        # extract gyfcat/redgifs/imgur url from embed data
                        embed_url = re.search(
                            "https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", embed_data)
                        if embed_url:
                            embed_url = URL(embed_url.group(
                                0).replace("www.", ""))
                            content_links.append([embed_url, temp_title])

                forum_direct_urls = [x for x in content_links if x[0].host in url.host]
                content_links = [x for x in content_links if x not in forum_direct_urls]
                for link_title_bundle in forum_direct_urls:
                    link = link_title_bundle[0]
                    temp_title = link_title_bundle[1]
                    in_prog_title = temp_title + "/Attachments"
                    if str(link).endswith("/"):
                        link = URL(str(link)[:-1])
                    if 'attachments' in link.parts:
                        await Cascade.add_to_album(url.host, in_prog_title, link, url)
                    if 'content' in link.parts:
                        await Cascade.add_to_album(url.host, in_prog_title, link, url)
                    elif 'data' in link.parts:
                        await Cascade.add_to_album(url.host, in_prog_title, link, url)

                tasks = []
                for link_title_bundle in content_links:
                    link = link_title_bundle[0]
                    temp_title = link_title_bundle[1]
                    tasks.append(self.scraping_mapper.map_url(link, temp_title))
                await asyncio.gather(*tasks)

                next_page = soup.select_one('a[class="pageNav-jump pageNav-jump--next"]')
                if next_page is not None:
                    next_page = next_page.get('href')
                    if next_page is not None:
                        if next_page.startswith('/'):
                            next_page = domain / next_page[1:]
                        next_page = URL(next_page)
                        title = await self.parse_thread(session, next_page, Cascade, title)
                return

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url))
            logger.debug(e)
