from scrapy import signals, Spider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.http.request import Request
from scrapy.signalmanager import dispatcher
from urllib.parse import urlparse
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
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

    def parse(self, response, **kwargs):
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
                yield {'netloc': netloc, 'url': link.replace('.md.', '.').replace('.th.', '.'), 'title': title, 'referal': response.url, 'cookies': ''}


class ShareXSingular(Spider):
    name = 'ShareX_Singular'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ShareXSingular, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.get_list_links)

    def get_list_links(self, response):
        link = response.css('input[id=embed-code-2]::attr(value)').getall()
        title = "ShareX Loose Files"
        netloc = urlparse(link).netloc.replace('www.', '')
        yield {'netloc': netloc, 'url': link.replace('.md.', '.').replace('.th.', '.'), 'title': title, 'referal': response.url, 'cookies': ''}


class ChibisafeSpider(Spider):
    name = 'Chibisafe'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ChibisafeSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.parse)

    def parse(self, response, **kwargs):
        links = response.css('a[class=image]::attr(href)').getall()
        title = response.css('h1[id=title]::text').get()
        title = title.replace(r"\n", "").strip()
        for link in links:
            netloc = urlparse(link).netloc.replace('www.', '')
            yield {'netloc': netloc, 'url': link, 'title': title, 'referal': response.url, 'cookies': ''}


class GoFileSpider(Spider):
    name = 'GoFile'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        super(GoFileSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.parse)

    def parse(self, response, **kwargs):
        self.driver.get(response.url)
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'contentId-download'))
        )
        cookies = self.driver.get_cookies()
        links = self.driver.find_elements(By.XPATH, "//button[@id='contentId-download']/..")
        title = self.driver.find_element(By.ID, 'rowFolder-folderName').text
        for link in links:
            link = link.get_attribute("href")
            netloc = urlparse(link).netloc.replace('www.', '')
            yield {'netloc': netloc, 'url': link, 'title': title, 'referal': response.url, 'cookies': cookies}
        self.driver.close()


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
    elif "gofile" in key:
        key = 'gofile.io'
    return key


def scrape(urls):
    mapping_ShareX = ["pixl.is", "putme.ga", "putmega.com"]
    mapping_Chibisafe = ["cyberdrop.me", "bunkr.is", "bunkr.to"]
    mapping_GoFile = ["gofile.io"]

    ShareX_album_urls = []
    ShareX_profile_albums = []
    ShareX_profile = []
    ShareX_singular_urls = []

    Chibisafe_urls = []
    GoFile_urls = []

    unsupported_urls = []

    cookies = []
    result_links = {}

    for url in urls:
        base_domain = urlparse(url).netloc.replace('www.', '')
        if base_domain in mapping_ShareX:
            if '/album/' in url:
                ShareX_album_urls.append(url)
            elif '/image/' in url:
                ShareX_singular_urls.append(url)
            elif '/albums' in url:
                ShareX_profile_albums.append(url)
            else:
                ShareX_profile.append(url)
        elif base_domain in mapping_Chibisafe:
            Chibisafe_urls.append(url)
        elif base_domain in mapping_GoFile:
            GoFile_urls.append(url)
        else:
            unsupported_urls.append(url)

    def crawler_results(signal, sender, item, response, spider):
        domain = sanitize_key(item['netloc'])
        title = re.sub(r'[\\/*?:"<>|.]', "-", item['title'])
        referal = item['referal']
        url = item['url']
        cookies.extend(x for x in item['cookies'] if x not in cookies)
        result_links.setdefault(domain, {}).setdefault(title, []).append([url, referal])

    dispatcher.connect(crawler_results, signal=signals.item_scraped)
    settings = get_project_settings()
    settings.set('LOG_LEVEL', logging.CRITICAL)
    process = CrawlerProcess(settings)
    if ShareX_album_urls: process.crawl(ShareXSpider, myurls=ShareX_album_urls)
    if ShareX_profile_albums: process.crawl(ShareXSpider, myurls=ShareX_album_urls)
    if ShareX_profile: process.crawl(ShareXSpider, myurls=ShareX_album_urls)
    if ShareX_singular_urls: process.crawl(ShareXSingular, myurls=ShareX_singular_urls)

    if Chibisafe_urls: process.crawl(ChibisafeSpider, myurls=Chibisafe_urls)
    if GoFile_urls: process.crawl(GoFileSpider, myurls=GoFile_urls)
    process.start()

    return cookies, result_links
