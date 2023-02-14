import html
import re


from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe, FILE_FORMATS, get_filename_and_ext, \
    get_db_path
from ..base_functions.data_classes import AlbumItem, MediaItem
from ..base_functions.error_classes import NoExtensionFailure
from ..base_functions.sql_helper import SQLHelper
from ..client.client import ScrapeSession


class BunkrCrawler:
    def __init__(self, quiet: bool, SQL_Helper: SQLHelper, remove_bunkr_id: bool):
        self.quiet = quiet
        self.SQL_Helper = SQL_Helper
        self.remove_bunkr_id = remove_bunkr_id

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
            check_complete = await self.SQL_Helper.check_complete_singular("bunkr", url.path)
            url = URL(str(url).replace("https://cdn", "https://i"))
            url = await self.check_for_la(url)

            filename, ext = await get_filename_and_ext(url.name)
            if self.remove_bunkr_id:
                filename = await self.remove_id(filename, ext)


        if "v" in url.parts or "d" in url.parts:
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
            files = soup.select('a[class*="grid-images_box-link"]')
            for file in files:
                link = file.get("href")

                if link.startswith("/"):
                    link = URL("https://" + url.host + link)
                link = URL(link)
                ext = '.' + str(link).split('.')[-1]
                ext = ext.lower()

                referrer = link

                if "v" in link.parts or "d" in link.parts:
                    link = await self.stream(session, link)

                else:
                    media_loc = file.select_one("img").get("src").split("//i")[-1].split(".bunkr.")[0]
                    referrer = link
                    if ext in FILE_FORMATS['Images']:
                        link = URL(str(link).replace("https://cdn", "https://i"))
                    else:
                        if media_loc != '12':
                            link = URL(f"https://media-files{media_loc}.bunkr.ru/" + link.name)
                        else:
                            link = URL(f"https://media-files{media_loc}.bunkr.la/" + link.name)

                await domain_obj.add_to_album(title, link, referrer)

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)
            return MediaItem(url, url, False, "", "")

    async def stream(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            head = soup.select_one("head")
            scripts = head.select('script[type="text/javascript"]')
            link = None

            for script in scripts:
                if script.text:
                    if "link.href" in script.text:
                        link = html.unescape(script.text.split('link.href = "')[-1].split('";')[0])
                        break
            if not link:
                raise
            link = URL(link, encoded=True)
            return link

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log(f"[red]Error: {str(url)}[/red]", quiet=self.quiet)
            logger.debug(e)

        return album
