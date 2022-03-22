from scrapy import signals, Spider
from scrapy.http.request import Request
from urllib.parse import urlparse
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
import re
import settings

title_setting = settings.include_id_in_download_folder_name


class GoFile_Spider(Spider):
    name = 'GoFile'

    def __init__(self, *args, **kwargs):
        self.myurls = kwargs.get('myurls', [])
        chromedriver_autoinstaller.install()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        super(GoFile_Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        for url in self.myurls:
            yield Request(url, self.parse)

    def parse(self, response, **kwargs):
        self.driver.get(response.url)
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'contentId-download'))
        )
        cookies = self.driver.get_cookies()
        folder_links = self.driver.find_elements(By.CSS_SELECTOR, "div[class='col-md text-center text-md-right'] a[class=ajaxLink]")
        links = self.driver.find_elements(By.XPATH, "//button[@id='contentId-download']/..")

        try:
            title = self.driver.find_element(By.ID, 'rowFolder-folderName').text
            if title_setting:
                title = title + " - " + response.url.split('/')[-1]
            title = re.sub(r'[/]', "-", title)
        except Exception as e:
            title = response.url.split('/')[-1]
        try:
            og_title = response.meta.get('title')
            title = og_title + "/" + title
        except:
            pass

        for folder_link in folder_links:
            link = folder_link.get_attribute("href")
            yield Request(link, self.parse, meta={'title': title})

        for link in links:
            link = link.get_attribute("href")
            if link is None:
                continue
            netloc = urlparse(link).netloc.replace('www.', '')
            yield {'netloc': netloc, 'url': link, 'title': title, 'referal': response.url, 'cookies': cookies}

    def closed(self, reason):
        self.driver.close()