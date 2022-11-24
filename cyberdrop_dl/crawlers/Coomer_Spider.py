import asyncio

from yarl import URL

from ..base_functions.base_functions import log, logger, make_title_safe
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class CoomerCrawler:
    def __init__(self, *, include_id=False, scraping_mapper, separate_posts=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet
        self.scraping_mapper = scraping_mapper
        self.separate_posts = separate_posts

    async def fetch(self, session: Session, url: URL):
        await log("Starting scrape of " + str(url), quiet=self.quiet)
        domain_obj = DomainItem('coomer.party', {})
        results = []

        if "thumbnail" in url.parts:
            parts = [x for x in url.parts if x not in ("thumbnail", "/")]
            link = URL("https://coomer.party/" + "/".join(parts))
            await domain_obj.add_to_album("Loose Coomer.Party Files", link, link)
        elif "data" in url.parts:
            await domain_obj.add_to_album("Loose Coomer.Party Files", url, url)
        elif "post" in url.parts:
            results = await self.parse_post(session, url, None)
            for result in results:
                await domain_obj.add_to_album(result[0], result[1], result[2])
        else:
            results.extend(await self.parse_profile(session, url))

        for result in results:
            await domain_obj.add_to_album(result[0], result[1], result[2])

        await log("Finished scrape of " + str(url), quiet=self.quiet)
        return domain_obj

    async def parse_profile(self, session: Session, url: URL):
        try:
            soup = await session.get_BS4(url)
            title = soup.select_one("span[itemprop=name]").get_text()
            title = title + " (Coomer.party)"
            results = []

            posts = []
            posts += soup.select("h2[class=post-card__heading] a")
            for post in posts:
                path = post.get('href')
                if path:
                    post_link = URL("https://coomer.party" + path)
                    results.extend(await self.parse_post(session, post_link, title))

            next_page = soup.select_one('a[title="Next page"]')
            if next_page:
                next_page = next_page.get('href')
                if next_page:
                    results.extend(await self.parse_profile(session, URL("https://coomer.party" + next_page)))
            return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []

    async def parse_post(self, session: Session, url: URL, title=None):
        try:
            await log("Scraping post: " + str(url), quiet=self.quiet)
            soup = await session.get_BS4(url)
            results = []

            if self.separate_posts:
                if title:
                    title = title + '/' + await make_title_safe(soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", ""))
                else:
                    title = await make_title_safe(soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", ""))
            else:
                if not title:
                    title = await make_title_safe(soup.select_one("h1[class=post__title]").text.replace('\n', '').replace("..", ""))

            images = soup.select('a[class="fileThumb"]')
            for image in images:
                image_link = URL("https://coomer.party" + image.get('href'))
                results.append([title, image_link, url])

            downloads = soup.select('a[class=post__attachment-link]')
            for download in downloads:
                download_link = URL("https://coomer.party" + download.get('href'))
                results.append([title, download_link, url])

            text_content = soup.select("div[class=post__content] a")
            tasks = []
            for content in text_content:
                link = URL(content.get('href'))
                tasks.append(self.scraping_mapper.map_url(link, title))
            await asyncio.gather(*tasks)

            return results

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
            return []
