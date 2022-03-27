import re
from urllib.parse import urljoin, urlparse

from scrapy import Spider
from scrapy.http.request import Request
import aiohttp
from bs4 import BeautifulSoup

from ..data_classes import *
from ..base_functions import *


class ChibisafeCrawler():
    def __init__(self, **kwargs):
        self.links: list[str] = kwargs.get("links", [])
        self.include_id = kwargs.get('include_id', False)
        self.results = {}



class Chibisafe_Spider(Spider):
    name = 'Chibisafe'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        self.include_id = kwargs.get('include_id', False)
        super(Chibisafe_Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            ext = "." + url.split('.')[-1]
            if '/a/' in url:
                yield Request(url, self.parse)
            elif ext in FILE_FORMATS['Images']:
                yield Request(url, self.individual_file)
            elif ext in FILE_FORMATS['Videos']:
                yield Request(url, self.individual_bunkr_video, meta={'dont_redirect': True, 'handle_httpstatus_list': [301, 302]})

    def individual_file(self, response):
        netloc = urlparse(response.url).netloc.replace('www.', '')
        title = "Chibisafe Loose Files"
        yield {'netloc': netloc, 'url': bunkr_parse(response.url), 'title': title, 'referal': response.url, 'cookies': ''}

    def individual_bunkr_video(self, response):
        netloc = urlparse(response.url).netloc.replace('www.', '')
        title = "Chibisafe Loose Files"
        link = response.url.replace('stream.bunkr.is/v/', 'media-files.bunkr.is/')
        yield {'netloc': netloc, 'url': bunkr_parse(link), 'title': title, 'referal': response.url, 'cookies': ''}

    def parse(self, response, **kwargs):
        links = response.css('a[class=image]::attr(href)').getall()

        try:
            title = response.css('h1[id=title]::text').get()
            title = title.replace(r"\n", "").strip()
            if self.include_id:
                title = title + " - " + response.url.split('/')[-1]
        except Exception as e:
            title = response.url.split('/')[-1]
        title = re.sub(r'[/]', "-", title)

        for link in links:
            netloc = urlparse(link).netloc.replace('www.', '')
            yield {'netloc': netloc, 'url': bunkr_parse(link), 'title': title, 'referal': response.url, 'cookies': ''}
