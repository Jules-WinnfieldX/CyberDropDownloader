from abc import ABC, abstractmethod
from typing import Iterable, Iterator, Optional, Set, Type
from types import TracebackType
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class Scraper(ABC):
    """This class handles scraping links from a given page."""
    def __init__(self, start_url: str):
        self.session = requests.Session()
        self.url = start_url

    def __enter__(self) -> 'Scraper':
        return self

    def __exit__(self, exc_type: Type[Exception], exc_val: Exception, exc_tb: TracebackType) -> None:
        self.session.close()

    def get_soup(self) -> BeautifulSoup:
        """Get the HTML from the url and return a BeautifulSoup from it

        Returns:
            BeautifulSoup
        """
        response = self.session.get(self.url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    def fetch_all_links(self) -> Iterator[Set[str]]:
        """Scrape the URL and generate a list of href links from found anchors per page.

        Yielding will change the internal url variable to next page (until we hit last page).

        Raises:
            ValueError: Url is not in sets
        Yields:
            Iterator[Set[str]]
        """
        yield self.get_page_links()

        if self.next_page_url is not None:
            self.url = self.next_page_url
            yield from self.fetch_all_links()

    @abstractmethod
    def get_page_links(self) -> Iterable[str]:
        """Scrape the page and return a list of href links from found anchors.

        This method is expected to be overridden since each site will have different
        structure and obtaining links will differ.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def next_page_url(self) -> Optional[str]:
        """
        Gets the URL for the next page scraped from current page.

        This method is expected to be overridden since each site will have the link
        to next page in a different place.

        If there is no next page, we return `None`
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def previous_page_url(self) -> Optional[str]:
        """Gets the URL for the previous page scraped from current page.

        This method is expected to be overridden since each site will have the link
        to next page in a different place.
        """

        raise NotImplementedError

    def result_links(self) -> Set[str]:
        """Get all links across all pages from the start page url.

        Returns:
            Set[str]: Set of urls
        """
        return {url for page_urls in self.fetch_all_links() for url in page_urls}


class ChibisafeScraper(Scraper):
    """Handles Scraping websites built on chibisafe project."""

    def get_page_links(self) -> Iterable[str]:
        soup = self.get_soup().select_one('#table')
        return {anchor['href'] for anchor in soup.findAll('a', href=True)}

    @property
    def next_page_url(self) -> Optional[str]:
        # Chibisafe project doesn't have pagination support
        return None

    @property
    def previous_page_url(self) -> Optional[str]:
        # Chibisafe project doesn't have pagination support
        return None


class SharexScraper(Scraper):
    """Handles scraping websites built on sharex project."""
    def get_page_links(self) -> Iterable[str]:
        soup = self.get_soup().select_one('#list-most-recent')
        return {
            anchor['src']
            for content in soup.findAll('div', {'class': 'pad-content-listing'})
            for anchor in content.find_all('img')
        }

    @property
    def next_page_url(self) -> Optional[str]:
        soup = self.get_soup().select_one('#list-most-recent')
        next_page = soup.find('a', {'data-pagination': 'next'}, href=True)
        if next_page is not None:
            return next_page.get('href')
        return None

    @property
    def previous_page_url(self) -> Optional[str]:
        # TODO: Implement this (even though it may not be needed at the moment
        # since we have next_page_url, it kind of makes sense to have previous
        # page too, you never know what you'll want to do with the class eventually
        # (or if it's a library, what others will want to do with it)
        raise NotImplementedError


def get_scrapper(url: str) -> Scraper:
    """This function is responsible for returning a proper Scrape class given the URL."""
    mapping = {
        "cyberdrop.me": ChibisafeScraper,
        "bunkr.is": ChibisafeScraper,
        "pixl.is": SharexScraper,
        "putme.ga": SharexScraper
    }
    url_netloc = urlparse(url).netloc
    return mapping[url_netloc](url)
