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
from collections import OrderedDict
import logging
import re
import settings


FILE_FORMATS = {
    'Images': {
        '.jpg', '.jpeg', '.png', '.gif',
        '.gif', '.webp', '.jpe', '.svg',
        '.tif', '.tiff', '.jif',
    },
    'Videos': {
        '.mpeg', '.avchd', '.webm', '.mpv',
        '.swf', '.avi', '.m4p', '.wmv',
        '.mp2', '.m4v', '.qt', '.mpe',
        '.mp4', '.flv', '.mov', '.mpg',
        '.ogg',
    },
    'Audio': {
        '.mp3', '.flac', '.wav', '.m4a'
    }
}


# Scrapes all files from an Album
class ShareX_Spider(Spider):
    name = 'ShareX'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ShareX_Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            if '/album/' in url:
                yield Request(url, self.parse)
            elif '/albums' in url:
                yield Request(url, self.get_albums)
            elif '/image/' in url:
                yield Request(url, self.get_singular)
            else:
                yield Request(url, self.parse_profile)

    def parse_profile(self, response):
        try:
            title = response.css('div[class=header] h1 strong::text').get()
            title = title.replace(r"\n", "").strip()
        except Exception as e:
            title = response.url.split('/')
            title = [s for s in title if "." in s][-1]

        list_recent = response.css('a[id=list-most-recent-link]::attr(href)').get()
        yield Request(list_recent, callback=self.get_list_links, meta={'title': title})

    def get_albums(self, response):
        albums = response.css("a[class='image-container --media']::attr(href)").getall()
        for url in albums:
            yield Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        try:
            title = response.css('a[data-text=album-name]::text').get()
            title = title.replace(r"\n", "").strip()
        except Exception as e:
            title = response.url.split('/')
            title = [s for s in title if "." in s][-1]

        list_recent = response.css('a[id=list-most-recent-link]::attr(href)').get()
        yield Request(list_recent, callback=self.get_list_links, meta={'title': title})

    def get_singular(self, response):
        link = response.css('input[id=embed-code-2]::attr(value)').get()
        title = "ShareX Loose Files"
        netloc = urlparse(link).netloc.replace('www.', '')
        yield {'netloc': netloc, 'url': link.replace('.md.', '.').replace('.th.', '.'), 'title': title, 'referal': response.url, 'cookies': ''}

    def get_list_links(self, response):
        links = response.meta.get('links', [])
        links.extend(response.css('a[href*=image] img::attr(src)').getall())
        title = response.meta.get('title')

        next_page = response.css('li.pagination-next a::attr("href")').get()
        meta = {'links': links, 'title': title}
        if next_page is not None:
            yield Request(url=next_page, callback=self.get_list_links, meta=meta)
        else:
            for link in links:
                netloc = urlparse(link).netloc.replace('www.', '')
                yield {'netloc': netloc, 'url': link.replace('.md.', '.').replace('.th.', '.'), 'title': title, 'referal': response.url, 'cookies': ''}


class ChibisafeSpider(Spider):
    name = 'Chibisafe'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        super(ChibisafeSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            ext = "."+url.split('.')[-1]
            if '/a/' in url:
                yield Request(url, self.parse)
            elif ext in FILE_FORMATS['Images']:
                yield Request(url, self.individual_file)
            elif ext in FILE_FORMATS['Videos']:
                yield Request(url, self.individual_bunkr_video, meta={'dont_redirect': True, 'handle_httpstatus_list': [301, 302]})

    def individual_file(self, response):
        netloc = urlparse(response.url).netloc.replace('www.', '')
        yield {'netloc': netloc, 'url': response.url, 'title': "Chibisafe Loose Files", 'referal': response.url, 'cookies': ''}

    def individual_bunkr_video(self, response):
        netloc = urlparse(response.url).netloc.replace('www.', '')
        yield {'netloc': netloc, 'url': response.url.replace('stream.bunkr.is/v/', 'media-files.bunkr.is/'), 'title': "Chibisafe Loose Files", 'referal': response.url, 'cookies': ''}

    def parse(self, response, **kwargs):
        links = response.css('a[class=image]::attr(href)').getall()
        try:
            title = response.css('h1[id=title]::text').get()
            title = title.replace(r"\n", "").strip()
        except Exception as e:
            title = response.url.split('/')[-1]
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

        try:
            title = self.driver.find_element(By.ID, 'rowFolder-folderName').text
        except Exception as e:
            title = response.url.split('/')[-1]

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


def check_direct(url):
    mapping_direct = ['i.pixl.is', r's..putmega.com', r's..putme.ga', r'img-...cyberdrop...', r'f.cyberdrop...', r'fs-...cyberdrop...', r'cdn.bunkr...', r'media-files.bunkr...']
    for domain in mapping_direct:
        if re.search(domain, url): return True
    return False


def scrape(urls):
    mapping_ShareX = ["pixl.is", "putme.ga", "putmega.com"]
    mapping_Chibisafe = ["cyberdrop.me", "cyberdrop.cc", "cyberdrop.to", "cyberdrop.nl", "bunkr.is", "bunkr.to"]
    mapping_GoFile = ["gofile.io"]

    replacements = [
        ('fs-...', ''),
        ('f\.', ''),
        ('img-...', ''),
        ('i\.', ''),
        ('stream\.', ''),
        ('media-files', ''),
        ('www\.', ''),
        ('cdn\.', ''),
        ('s.\.', '')
    ]

    ShareX_urls = []
    Chibisafe_urls = []
    GoFile_urls = []
    unsupported_urls = []

    cookies = []
    result_links = OrderedDict()

    for url in urls:
        url = url.replace('\n', '')
        base_domain = urlparse(url).netloc
        for old, new in replacements:
            base_domain = re.sub(old, new, base_domain)
        if base_domain in mapping_ShareX:
            if check_direct(url):
                result_links.setdefault(base_domain, OrderedDict()).setdefault("ShareX Loose Files", []).append([url, url])
            else:
                ShareX_urls.append(url)
        elif base_domain in mapping_Chibisafe:
            if check_direct(url):
                result_links.setdefault(base_domain, OrderedDict()).setdefault("Chibisafe Loose Files", []).append([url, url])
            else:
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
        result_links.setdefault(domain, OrderedDict()).setdefault(title, []).append([url, referal])

    dispatcher.connect(crawler_results, signal=signals.item_scraped)
    settings = get_project_settings()
    settings.set('LOG_FILE', 'logs.log')
    process = CrawlerProcess(settings)

    if ShareX_urls: process.crawl(ShareX_Spider, myurls=ShareX_urls)
    if Chibisafe_urls: process.crawl(ChibisafeSpider, myurls=Chibisafe_urls)
    if GoFile_urls: process.crawl(GoFileSpider, myurls=GoFile_urls)
    process.start()

    return cookies, result_links
