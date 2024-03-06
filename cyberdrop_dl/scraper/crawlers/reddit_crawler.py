from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
import asyncpraw
import asyncprawcore
from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import ScrapeFailure, NoExtensionFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, log, get_filename_and_ext

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class RedditCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "reddit", "Reddit")
        self.reddit_personal_use_script = self.manager.config_manager.authentication_data['Reddit']['reddit_personal_use_script']
        self.reddit_secret = self.manager.config_manager.authentication_data['Reddit']['reddit_secret']
        self.request_limiter = AsyncLimiter(5, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if not self.reddit_personal_use_script or not self.reddit_secret:
            await log("Reddit API credentials not found. Skipping.", 30)
            await self.manager.progress_manager.scrape_stats_progress.add_failure("Failed Login")
            await self.scraping_progress.remove_task(task_id)
            return

        async with aiohttp.ClientSession() as reddit_session:
            reddit = asyncpraw.Reddit(client_id=self.reddit_personal_use_script,
                                      client_secret=self.reddit_secret,
                                      user_agent="CyberDrop-DL",
                                      requestor_kwargs={"session": reddit_session},
                                      check_for_updates=False)

            if "user" in scrape_item.url.parts or "u" in scrape_item.url.parts:
                await self.user(scrape_item, reddit)
            elif "r" in scrape_item.url.parts and "comments" not in scrape_item.url.parts:
                await self.subreddit(scrape_item, reddit)
            elif "redd.it" in scrape_item.url.host:
                await self.media(scrape_item, reddit)
            else:
                await log(f"Scrape Failed: Unknown URL Path for {scrape_item.url}", 40)
                await self.manager.progress_manager.scrape_stats_progress.add_failure("Unknown")

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def user(self, scrape_item: ScrapeItem, reddit: asyncpraw.Reddit) -> None:
        """Scrapes user pages"""
        username = scrape_item.url.name
        title = await self.create_title(username, None, None)
        await scrape_item.add_to_parent_title(title)
        scrape_item.part_of_album = True

        user = await reddit.redditor(username)
        submissions = user.submissions.new(limit=None)
        await self.get_posts(scrape_item, submissions, reddit)

    @error_handling_wrapper
    async def subreddit(self, scrape_item: ScrapeItem, reddit: asyncpraw.Reddit) -> None:
        """Scrapes subreddit pages"""
        subreddit = scrape_item.url.name
        title = await self.create_title(subreddit, None, None)
        await scrape_item.add_to_parent_title(title)
        scrape_item.part_of_album = True

        subreddit = await reddit.subreddit(subreddit)
        submissions = subreddit.new(limit=None)
        await self.get_posts(scrape_item, submissions, reddit)

    @error_handling_wrapper
    async def get_posts(self, scrape_item: ScrapeItem, submissions, reddit: asyncpraw.Reddit) -> None:
        try:
            submissions = [submission async for submission in submissions]
        except asyncprawcore.exceptions.Forbidden:
            raise ScrapeFailure(403, "Forbidden")
        except asyncprawcore.exceptions.NotFound:
            raise ScrapeFailure(404, "Not Found")

        for submission in submissions:
            await self.post(scrape_item, submission, reddit)

    @error_handling_wrapper
    async def post(self, scrape_item: ScrapeItem, submission, reddit: asyncpraw.Reddit) -> None:
        """Scrapes posts"""
        title = submission.title
        date = int(str(submission.created_utc).split(".")[0])

        try:
            media_url = URL(submission.media['reddit_video']['fallback_url'])
        except (KeyError, TypeError):
            media_url = URL(submission.url)

        if "v.redd.it" in media_url.host:
            filename, ext = await get_filename_and_ext(media_url.name)

        if "redd.it" in media_url.host:
            new_scrape_item = await self.create_new_scrape_item(media_url, scrape_item, title, date)
            await self.media(new_scrape_item, reddit)
        elif "gallery" in media_url.parts:
            new_scrape_item = await self.create_new_scrape_item(media_url, scrape_item, title, date)
            await self.gallery(new_scrape_item, submission, reddit)
        else:
            if "reddit.com" not in media_url.host:
                new_scrape_item = await self.create_new_scrape_item(media_url, scrape_item, title, date)
                await self.handle_external_links(new_scrape_item)

    async def gallery(self, scrape_item: ScrapeItem, submission, reddit: asyncpraw.Reddit) -> None:
        """Scrapes galleries"""
        if not hasattr(submission, "media_metadata") or submission.media_metadata is None:
            return
        items = [item for item in submission.media_metadata.values() if item["status"] == "valid"]
        links = [URL(item["s"]["u"]).with_host("i.redd.it").with_query(None) for item in items]
        for link in links:
            new_scrape_item = await self.create_new_scrape_item(link, scrape_item, scrape_item.parent_title, scrape_item.possible_datetime)
            await self.media(new_scrape_item, reddit)

    @error_handling_wrapper
    async def media(self, scrape_item: ScrapeItem, reddit: asyncpraw.Reddit) -> None:
        """Handles media links"""
        try:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
        except NoExtensionFailure:
            head = await self.client.get_head(self.domain, scrape_item.url)
            head = await self.client.get_head(self.domain, head['location'])

            try:
                post = await reddit.submission(url=head['location'])
            except asyncprawcore.exceptions.Forbidden:
                raise ScrapeFailure(403, "Forbidden")
            except asyncprawcore.exceptions.NotFound:
                raise ScrapeFailure(404, "Not Found")

            await self.post(scrape_item, post, reddit)
            return

        await self.handle_file(scrape_item.url, scrape_item, filename, ext)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def create_new_scrape_item(self, link: URL, old_scrape_item: ScrapeItem, title: str, date: int) -> ScrapeItem:
        """Creates a new scrape item with the same parent as the old scrape item"""

        new_scrape_item = await self.create_scrape_item(old_scrape_item, link, "", True, None, date)
        if self.manager.config_manager.settings_data['Download_Options']['separate_posts']:
            await new_scrape_item.add_to_parent_title(title)
        return new_scrape_item
