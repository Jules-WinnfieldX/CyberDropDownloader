from collections import OrderedDict
import logging
import re
from urllib.parse import urlparse

from colorama import Fore, Style
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher
from scrapy.utils.project import get_project_settings

from .crawlers.ShareX_Spider import ShareX_Spider
from .crawlers.Erome_Spider import Erome_Spider
from .crawlers.Chibisafe_Spider import Chibisafe_Spider
from .crawlers.GoFile_Spider import GofileCrawler


logger = logging.getLogger(__name__)

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


def log(text, style):
    # Log function for printing to command line
    print(style + str(text) + Style.RESET_ALL)


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
        key = "gofile.io"
    elif "church" in key:
        key = "jpg.church"
    elif "erome" in key:
        key = "erome.com"
    return key


def check_direct(url):
    mapping_direct = ['i.pixl.is', r's..putmega.com', r's..putme.ga', r'img-...cyberdrop...', r'f.cyberdrop...',
                      r'fs-...cyberdrop...', r'cdn.bunkr...', r'media-files.bunkr...', r'jpg.church/images/...']
    for domain in mapping_direct:
        if re.search(domain, url):
            return True
    return False


def scrape(urls, include_id: bool):
    mapping_ShareX = ["pixl.is", "putme.ga", "putmega.com", "jpg.church"]
    mapping_Chibisafe = ["cyberdrop.me", "cyberdrop.cc", "cyberdrop.to", "cyberdrop.nl", "bunkr.is", "bunkr.to"]
    mapping_Erome = ["erome.com"]
    mapping_GoFile = ["gofile.io"]
    mapping_Pixeldrain = ["pixeldrain.com"]

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
    Erome_urls = []
    GoFile_urls = []
    Pixeldrain_urls = []
    unsupported_urls = []

    cookies = []
    result_links = OrderedDict()

    log("Starting Scrape", Fore.WHITE)

    for url in urls:
        url = url.replace('\n', '')
        base_domain = urlparse(url).netloc
        for old, new in replacements:
            base_domain = re.sub(old, new, base_domain)
        if base_domain in mapping_ShareX:
            if check_direct(url):
                result_links.setdefault(base_domain, OrderedDict()).setdefault("ShareX Loose Files", []).append(
                    [url, url])
            else:
                ShareX_urls.append(url)
        elif base_domain in mapping_Chibisafe:
            if check_direct(url):
                result_links.setdefault(base_domain, OrderedDict()).setdefault("Chibisafe Loose Files", []).append(
                    [url, url])
            else:
                Chibisafe_urls.append(url)
        elif base_domain in mapping_Erome:
            Erome_urls.append(url)
        elif base_domain in mapping_GoFile:
            GoFile_urls.append(url)
        elif base_domain in mapping_Pixeldrain:
            Pixeldrain_urls.append(url)
        else:
            unsupported_urls.append(url)

    def crawler_results(item):
        domain = sanitize_key(item['netloc'])
        title = re.sub(r'[\\*?:"<>|.]', "-", item['title'])
        referal = item['referal']
        url = item['url']
        cookies.extend(x for x in item['cookies'] if x not in cookies)
        result_links.setdefault(domain, OrderedDict()).setdefault(title, []).append([url, referal])

    dispatcher.connect(crawler_results, signal=signals.item_scraped)
    settings = get_project_settings()
    settings.set('LOG_FILE', 'downloader.log')
    settings.set('TWISTED_REACTOR', "twisted.internet.asyncioreactor.AsyncioSelectorReactor")
    process = CrawlerProcess(settings)

    if ShareX_urls:
        process.crawl(ShareX_Spider, myurls=ShareX_urls, include_id=include_id)
    if Chibisafe_urls:
        process.crawl(Chibisafe_Spider, myurls=Chibisafe_urls, include_id=include_id)
    if Erome_urls:
        process.crawl(Erome_Spider, myurls=Erome_urls, include_id=include_id)
    if GoFile_urls:
        gofile_crawler = GofileCrawler(links=GoFile_urls, include_id=include_id)
        result_links.setdefault('gofile.io', gofile_crawler.build_targets())
        cookies.append({
            'name': 'accountToken',
            'value': gofile_crawler.client.token,
        })
    if Pixeldrain_urls:
        for url in Pixeldrain_urls:
            folder = url.split('/')[-1]
            if url.split('/')[-2] == 'l':
                result_links.setdefault('pixeldrain.com', OrderedDict()).setdefault("PixelDrain", []).append([f'https://pixeldrain.com/api/list/{folder}/zip', url])
            else:
                result_links.setdefault('pixeldrain.com', OrderedDict()).setdefault("PixelDrain", []).append([f'https://pixeldrain.com/api/file/{folder}?download', url])

    process.start()

    return cookies, result_links
