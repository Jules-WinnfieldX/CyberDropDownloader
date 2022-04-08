import asyncio
from bs4 import BeautifulSoup

from .ShareX_Spider import ShareXCrawler
from .Erome_Spider import EromeCrawler
from .Chibisafe_Spider import ChibisafeCrawler
from .GoFile_Spider import GofileCrawler
from .Anonfiles_Spider import AnonfilesCrawler
from ..base_functions import *
from ..data_classes import *


class ThotsbayCrawler():
    def __init__(self, *, include_id=False, username=None, password=None, erome_crawler: EromeCrawler,
                 sharex_crawler: ShareXCrawler, chibisafe_crawler: ChibisafeCrawler, gofile_crawler: GofileCrawler,
                 anonfiles_crawler: AnonfilesCrawler):
        self.include_id = include_id
        self.username = username
        self.password = password
        self.erome_crawler = erome_crawler
        self.sharex_crawler = sharex_crawler
        self.chibisafe_crawler = chibisafe_crawler
        self.gofile_crawler = gofile_crawler
        self.anonfiles_crawler = anonfiles_crawler

    async def login(self, session):
        async with session.get("https://forum.thotsbay.com/login", ssl=ssl_context) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')

            inputs = soup.select('form input')
            data = {
                elem['name']: elem['value']
                for elem in inputs
                if elem.get('name') and elem.get('value')
            }
            data.update({"login": self.username, "password": self.password})
            return await session.post("https://forum.thotsbay.com/login/login", data=data)

    async def fetch(self, session, url):
        Cascade = CascadeItem({})

        log("Starting scrape of " + str(url), Fore.WHITE)
        logging.debug("Starting scrape of " + str(url))

        if self.username and self.password:
            await self.login(session)
        else:
            log("login wasn't provided, consider using --thotsbay-username and --thotsbay-password")
            log("Not being logged in might cause issues.")
            logger.debug("No login provided - Thotsbay.")

        try:
            ShareX_urls, Chibisafe_urls, Erome_urls, GoFile_urls, Thotsbay_urls, Anonfile_urls, title = await self.parse(session, url, Cascade, None)
        except:
            log("Error handling " + str(url))
            logger.debug("Error handling " + str(url))
            return
        tasks = []
        for url in Erome_urls:
            tasks.append(self.erome_crawler.fetch(session, url))
        for url in ShareX_urls:
            tasks.append(self.sharex_crawler.fetch(session, url))
        for url in Chibisafe_urls:
            tasks.append(self.chibisafe_crawler.fetch(session, url))
        for url in GoFile_urls:
            tasks.append(self.gofile_crawler.fetch(session, url))
        for url in Anonfile_urls:
            tasks.append(self.anonfiles_crawler.fetch(session, url))
        results = await asyncio.gather(*tasks)

        for result in results:
            Cascade.add_albums(result)

        Cascade.append_title(title)

        log("Finished scrape of " + str(url), Fore.WHITE)
        logging.debug("Finished scrape of " + str(url))

        return Cascade

    async def parse(self, session, url, Cascade, title):
        try:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')

                if title:
                    pass
                else:
                    title = soup.find('title').text
                    if self.include_id:
                        titlep2 = url.name
                        titlep2 = [s for s in titlep2 if "." in s][-1]
                        title = title + " - " + titlep2
                    title = make_title_safe(title.replace(r"\n", "").strip())

                content_links = []

                post_number = str(url).split("post-")
                post_number = int(post_number[-1]) if len(post_number) == 2 else None

                posts = soup.select("div[class='message-main uix_messageContent js-quickEditTarget']")
                for post in posts:
                    if post_number:
                        post_num_int = post.select_one("li[class=u-concealed] a")
                        post_num_int = int(post_num_int.get('href').split('post-')[-1])
                        if post_number > post_num_int:
                            continue
                    for elem in post.find_all('blockquote'):
                        elem.decompose()
                    post_content = post.select_one("div[class=bbWrapper]")
                    links = post_content.select('a')
                    for link in links:
                        link = link.get('href')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = URL("https://forum.thotsbay.com") / link[1:]
                        content_links.append(URL(link))
                    links = post.select("div[class='bbImageWrapper js-lbImage']")
                    for link in links:
                        link = link.get('data-src')
                        if link.endswith("/"):
                            link = link[:-1]
                        content_links.append(URL(link))
                    links = post.select("video source")
                    for link in links:
                        link = link.get('src')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('//'):
                            link = "https:" + link
                        elif link.startswith('/'):
                            link = "https://forum.thotsbay.com" + link
                        content_links.append(URL(link))

                    attachments_block = post.select_one("section[class=message-attachments]")
                    links = attachments_block.select("a[class='file-preview js-lbImage']") if attachments_block else []
                    for link in links:
                        link = link.get('href')
                        if link.endswith("/"):
                            link = link[:-1]
                        if link.startswith('/'):
                            link = URL("https://forum.thotsbay.com") / link[1:]
                        Cascade.add_to_album("Thotsbay.com", "Attachments", link, url)

                ShareX_urls, Chibisafe_urls, Erome_urls, GoFile_urls, Thotsbay_urls, Anonfile_urls = url_sort(content_links, Cascade)

                for link in Thotsbay_urls:
                    if str(link).endswith("/"):
                        link = URL(str(link)[:-1])
                    if 'attachments' in link.parts:
                        Cascade.add_to_album("Thotsbay.com", "Attachments", link, url)
                    elif 'data' in link.parts:
                        Cascade.add_to_album("Thotsbay.com", "Attachments", link, url)

                next_page = soup.select_one('a[class="pageNav-jump pageNav-jump--next"]')
                if next_page is not None:
                    next_page = next_page.get('href')
                    if next_page is not None:
                        if next_page.startswith('/'):
                            next_page = URL("https://forum.thotsbay.com") / next_page[1:]
                        next_page = URL(next_page)
                        ShareX_urls_ret, Chibisafe_urls_ret, Erome_urls_ret, GoFile_urls_ret, Thotsbay_urls_ret, Anonfile_urls_ret, title = await self.parse(session, next_page, Cascade, title)
                        ShareX_urls.extend(ShareX_urls_ret)
                        Chibisafe_urls.extend(Chibisafe_urls_ret)
                        Erome_urls.extend(Erome_urls_ret)
                        GoFile_urls.extend(GoFile_urls_ret)
                        Thotsbay_urls.extend(Thotsbay_urls_ret)
                        Anonfile_urls.extend(Anonfile_urls_ret)
                return ShareX_urls, Chibisafe_urls, Erome_urls, GoFile_urls, Thotsbay_urls, Anonfile_urls, title

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            logger.debug(e)
