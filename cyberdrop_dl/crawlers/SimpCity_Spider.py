import asyncio
import re

from bs4 import BeautifulSoup
from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, write_last_post_file
from ..base_functions.data_classes import AuthData, CascadeItem
from ..client.client import Session


class SimpCityCrawler:
    def __init__(self, *, include_id=False, auth: AuthData = None, scraping_mapper, separate_posts=False,
                 output_last=[False, None], quiet: bool):
        self.include_id = include_id
        self.quiet = quiet
        self.separate_posts = separate_posts
        self.output_last = output_last
        self.username, self.password = (auth.username, auth.password) if auth else (None, None)
        self.scraping_mapper = scraping_mapper
        self.lock = 0

    async def login(self, session: Session, url: URL):
        domain = URL("https://" + url.host) / "login"
        text = await session.get_text(domain)
        if "You are already logged in" in text:
            return
        soup = BeautifulSoup(text, 'html.parser')

        inputs = soup.select('form input')
        data = {
            elem['name']: elem['value']
            for elem in inputs
            if elem.get('name') and elem.get('value')
        }
        data.update({"login": self.username, "password": self.password, "_xfRedirect": str(domain)})
        return await session.post_data_no_resp(domain/"login", data=data)

    async def fetch(self, session: Session, url: URL):
        await log("Starting scrape of " + str(url), quiet=self.quiet)
        cascade = CascadeItem({})

        try:
            if self.username and self.password:
                while True:
                    if self.lock == 0:
                        self.lock = 1
                        await self.login(session, url)
                        self.lock = 0
                        break
                    await asyncio.sleep(2)
            else:
                await log("login wasn't provided, consider using --simpcity-username and --simpcity-password", quiet=self.quiet)
                await log("Not being logged in might cause issues.", quiet=self.quiet)
            await self.parse_thread(session, url, cascade, "")
        except Exception as e:
            self.lock = 0
            await log(f"there was an error signing into {url.host}", quiet=self.quiet)
            await log(e, quiet=self.quiet)
            return

        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return cascade

    async def parse_thread(self, session: Session, url: URL, cascade: CascadeItem, title: str):
        try:
            soup = await session.get_BS4(url)

            domain = URL("https://" + url.host)

            title_block = soup.select_one("h1[class=p-title-value]")
            for elem in title_block.find_all("a"):
                elem.decompose()

            if title:
                pass
            else:
                title = title_block.text
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
                    await cascade.add_to_album(url.host, in_prog_title, URL(link), url)

                links = post_content.select("span[data-s9e-mediaembed-iframe]")
                for link in links:
                    embed_data = link.get("data-s9e-mediaembed-iframe")
                    embed_data = embed_data.replace("\/\/", "https://www.")
                    embed_data = embed_data.replace("\\", "")

                    embed_url = re.search(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", embed_data)
                    if embed_url:
                        embed_url = URL(embed_url.group(0).replace("www.", ""))
                        content_links.append([embed_url, temp_title])

                    embed_url = re.search(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\/[-a-zA-Z0-9@:%._\+~#=]*\/[-a-zA-Z0-9@:?&%._\+~#=]*", embed_data)
                    if embed_url:
                        embed_url = URL(embed_url.group(0).replace("www.", ""))
                        content_links.append([embed_url, temp_title])

            forum_direct_urls = [x for x in content_links if x[0].host.replace(".st", ".su") in url.host]
            content_links = [x for x in content_links if x not in forum_direct_urls]
            for link_title_bundle in forum_direct_urls:
                link = link_title_bundle[0]
                temp_title = link_title_bundle[1]
                in_prog_title = temp_title + "/Attachments"
                if str(link).endswith("/"):
                    link = URL(str(link)[:-1])
                if 'attachments' in link.parts:
                    await cascade.add_to_album(url.host, in_prog_title, link, url)
                if 'content' in link.parts:
                    await cascade.add_to_album(url.host, in_prog_title, link, url)
                elif 'data' in link.parts:
                    await cascade.add_to_album(url.host, in_prog_title, link, url)

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
                    title = await self.parse_thread(session, next_page, cascade, title)
            else:
                if self.output_last[0]:
                    if 'page-' in url.raw_name:
                        last_post_url = url.parent / post_num_str
                    elif 'post-' in url.raw_name:
                        last_post_url = url.parent / post_num_str
                    else:
                        last_post_url = url / post_num_str
                    await write_last_post_file(self.output_last[1], str(last_post_url))

            return

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
