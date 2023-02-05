import json
import re

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, check_direct, FILE_FORMATS
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class BunkrCrawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        domain_obj = DomainItem(url.host, {})
        await log("Starting scrape of " + str(url), quiet=self.quiet)

        cdn_possibilities = r"(?:cdn.bunkr...|cdn..bunkr...|cdn...bunkr...)"
        ext = '.' + str(url).split('.')[-1]
        ext = ext.lower()
        if ext in FILE_FORMATS['Videos']:
            url = URL(re.sub(cdn_possibilities, "bunkr.su/v", str(url)))
        if ext in FILE_FORMATS['Other']:
            url = URL(re.sub(cdn_possibilities, "bunkr.su/d", str(url)))
        if ext in FILE_FORMATS['Images']:
            url = URL(str(url).replace("https://cdn", "https://i"))

        if await check_direct(url):
            await domain_obj.add_to_album(link=url, referral=url, title="Bunkr Loose Files")
            return domain_obj

        if "v" in url.parts or "d" in url.host:
            link = await self.stream(session, url)
            await domain_obj.add_to_album(link=link, referral=url, title="Bunkr Loose Files")
            await log("Finished scrape of " + str(url), quiet=self.quiet)
            return domain_obj

        if "a" in url.parts:
            await self.album(session, url, domain_obj)

        await log("Finished scrape of " + str(url), quiet=self.quiet)

        return domain_obj

    async def album(self, session, url: URL, domain_obj: DomainItem):
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one('h1[class="text-[24px] font-bold text-dark dark:text-white"]')
            for elem in title.find_all("span"):
                elem.decompose()
            title = await make_title_safe(title.get_text())
            for file in soup.select('figure[class="relative w-full"] a'):
                link = file.get("href")

                media_loc = file.select_one("img").get("src").split("//i")[-1].split(".bunkr.")[0]

                temp_partial_link = link
                if link.startswith("/"):
                    link = URL("https://" + url.host + link)
                link = URL(link)
                ext = '.' + str(link).split('.')[-1]
                ext = ext.lower()

                referrer = link
                if "cdn" in link.host:
                    link = URL(str(link).replace("https://cdn", "https://i"))
                else:
                    link = URL(f"https://media-files{media_loc}.bunkr.ru" + temp_partial_link[2:])

                await domain_obj.add_to_album(title, link, referrer)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)

    async def stream(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            head = soup.select_one("head")
            scripts = soup.select('script[type="text/javascript"]')
            link = None

            for script in scripts:
                if script.text:
                    if "link.href" in script.text:
                        link = script.text.split('link.href = "')[-1].split('";')[0]
                        break
            if not link:
                raise
            link = URL(link)
            return link

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
