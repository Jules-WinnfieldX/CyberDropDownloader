from scrapy import signals, Spider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.http.request import Request
from scrapy.signalmanager import dispatcher
from urllib.parse import urlparse
import logging
import re


class ShareXSpider(Spider):
    name = 'ShareX'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ShareXSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.parse)

    def parse(self, response):
        list_recent = response.css('a[id=list-most-recent-link]::attr(href)').get()
        title = response.css('a[data-text=album-name]::text').get()
        title = title.replace(r"\n", "").strip()
        yield Request(list_recent, callback=self.get_list_links, meta={'title': title})

    def get_list_links(self, response):
        links = response.meta.get('links', [])
        title = response.meta.get('title')
        links.extend(response.css('a[href*=image] img::attr(src)').getall())

        next_page = response.css('li.pagination-next a::attr("href")').get()
        meta = {'links': links, 'title': title}
        if next_page is not None:
            yield Request(url=next_page, callback=self.get_list_links, meta=meta)
        else:
            for link in links:
                netloc = urlparse(link).netloc.replace('www.', '')
                yield {'netloc': netloc, 'url': link.replace('.md.', '.').replace('.th.', '.'), 'title': title}


class ChibisafeSpider(Spider):
    name = 'ShareX'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ChibisafeSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.parse)

    def parse(self, response):
        links = response.css('a[class=image]::attr(href)').getall()
        title = response.css('h1[id=title]::text').get()
        title = title.replace(r"\n", "").strip()
        for link in links:
            netloc = urlparse(link).netloc.replace('www.', '')
            yield {'netloc': netloc, 'url': link, 'title': title}


def sanitize_key(key):
    if "bunkr" in key:
        key = "bunkr.is"
    elif "pixl" in key:
        key = "pixl.is"
    elif "cyberdrop" in key:
        key = "cyberdrop.to"
    elif "putme.ga" in key:
        key = "putme.ga"
    elif "putmega" in key:
        key = 'putme.ga'
    return key


def scrape(urls):
    mapping_ShareX = ["pixl.is", "putme.ga", "putmega.com"]
    mapping_Chibisafe = ["cyberdrop.me", "bunkr.is", "bunkr.to"]


    ShareX_urls = []
    Chibisafe_urls = []
    unsupported_urls = []
    result_links = {}

    for url in urls:
        base_domain = urlparse(url).netloc.replace('www.', '')
        if base_domain in mapping_ShareX:
            ShareX_urls.append(url)
        elif base_domain in mapping_Chibisafe:
            Chibisafe_urls.append(url)
        else:
            unsupported_urls.append(url)

    def crawler_results(signal, sender, item, response, spider):
        domain = sanitize_key(item['netloc'])
        title = re.sub(r'[\\/*?:"<>|.]', "-", item['title'])
        result_links.setdefault(domain, {}).setdefault(title, []).append(item['url'])

    dispatcher.connect(crawler_results, signal=signals.item_scraped)
    settings = get_project_settings()
    settings.set('LOG_LEVEL', logging.CRITICAL)
    process = CrawlerProcess(settings)
    if Chibisafe_urls: process.crawl(ChibisafeSpider, myurls=Chibisafe_urls)
    if ShareX_urls: process.crawl(ShareXSpider, myurls=ShareX_urls)
    process.start()
    return result_links
