import re
from urllib.parse import urlparse

from scrapy import Spider
from scrapy.http.request import Request

class ShareX_Spider(Spider):
    name = 'ShareX'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        self.include_id = kwargs.get('include_id', False)
        super(ShareX_Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            if '/album/' in url or '/a/' in url:
                yield Request(url, self.parse)
            elif '/albums' in url:
                yield Request(url, self.get_albums)
            elif '/image/' in url or '/img/' in url or '/images/' in url:
                yield Request(url, self.get_singular)
            else:
                yield Request(url, self.parse_profile)

    def parse_profile(self, response):
        try:
            title = response.css('div[class=header] h1 strong::text').get()
            title = title.replace(r"\n", "").strip()
            if self.include_id:
                titlep2 = response.url.split('/')
                titlep2 = [s for s in titlep2 if "." in s][-1]
                title = title + " - " + titlep2
        except Exception as e:
            title = response.url.split('/')
            title = [s for s in title if "." in s][-1]
        title = re.sub(r'[/]', "-", title)

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
            if self.include_id:
                titlep2 = response.url.split('/')
                titlep2 = [s for s in titlep2 if "." in s][-1]
                title = title + " - " + titlep2
        except Exception as e:
            title = response.url.split('/')
            title = [s for s in title if "." in s][-1]
        title = re.sub(r'[/]', "-", title)

        try:
            title = response.meta.get('title') + "/" + title
        except:
            pass

        sub_albums = response.css('a[id=tab-sub-link]::attr(href)').get()
        yield Request(sub_albums, callback=self.get_sub_albums_links, meta={'title': title}, dont_filter=True)

        list_recent = response.css('a[id=list-most-recent-link]::attr(href)').get()
        yield Request(list_recent, callback=self.get_list_links, meta={'title': title})

    def get_singular(self, response):
        link = response.css('input[id=embed-code-2]::attr(value)').get()
        link = link.replace('.md.', '.').replace('.th.', '.')
        title = "ShareX Loose Files"
        netloc = urlparse(link).netloc.replace('www.', '')
        yield {'netloc': netloc, 'url': link, 'title': title, 'referal': response.url, 'cookies': ''}

    def get_sub_albums_links(self, response):
        albums = response.css('div[class=pad-content-listing] div::attr(data-url-short)').getall()
        for album in albums:
            yield Request(album, self.parse, meta=response.meta)

    def get_list_links(self, response):
        links = response.meta.get('links', [])
        if 'jpg.church' in response.url:
            links.extend(response.css('a[href*=img] img::attr(src)').getall())
        else:
            links.extend(response.css('a[href*=image] img::attr(src)').getall())
        title = response.meta.get('title')

        next_page = response.css('li.pagination-next a::attr("href")').get()
        meta = {'links': links, 'title': title}
        if next_page is not None:
            yield Request(url=next_page, callback=self.get_list_links, meta=meta)
        else:
            for link in links:
                netloc = urlparse(link).netloc.replace('www.', '')
                link = link.replace('.md.', '.').replace('.th.', '.')
                yield {'netloc': netloc, 'url': link, 'title': title, 'referal': response.url, 'cookies': ''}
