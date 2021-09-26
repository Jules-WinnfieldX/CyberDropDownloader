import requests
import os
from bs4 import BeautifulSoup, SoupStrainer

videoExtensions = ['.mp4', '.wmv', '.m4v']


def Extrair_Links(baseURL):
    # Extract links from gallery
    try:
        page = requests.get(baseURL)
        data = page.text
        soup = BeautifulSoup(data, features="html5lib")
        links = []
        pages = []

        # If cyberdrop, find id="file" href links
        if 'cyberdrop' in baseURL.lower():
            for link in soup.find_all(id="file"):
                lis = link.get('href')
                if len(str(lis)) > 30:
                    lis = lis.replace('.nl/', '.cc/')
                    links.append(lis)

        # If bunkr or bunkerleaks, find class="image" href links
        elif 'bunk' in baseURL.lower():
            for link in soup.find_all(class_="image"):
                lis = link.get('href')
                if '.mp4' in lis:
                    lis = lis.replace('https://cdn.bunkr.to/', 'https://cdn.bunkr.to/s/')
                links.append(lis)

        # If dmca.gripe find 'a', {'class': 'download-button'} href links
        elif 'dmca.gripe' in baseURL.lower():
            for link in soup.find_all('a', {'class': 'download-button'}):
                lis = link.get('href')
                if any(videoExtension in lis for videoExtension in videoExtensions):
                    # if it's a video, redo the process in gripeVideo
                    links.append(gripeVideo(lis))
                elif len(str(lis)) > 30:
                    links.append(lis)

        # If putme.ga or pixl, correct any bad urls, find all pages in album,
        # find all image links and then correct all image links
        elif 'putme.ga' or 'pixl' in baseURL.lower():
            # First correct any 'bad' URLs by getting the real embedded url from the page itself
            url = soup.find(attrs={"data-text": "album-name"}).get('href')
            pages.append(url)

            # Find all the pages within the album
            while True:
                # Searches for links within the page
                request = requests.get(url)
                soup = BeautifulSoup(request.text, 'html.parser')
                # Searches for next page link
                nextPage = soup.find("li", {'class': 'pagination-next'})
                if nextPage is None:
                    break
                else:
                    for child in nextPage.children:
                        childURL = child.get("href")
                        if childURL:
                            pages.append(childURL)
                    if not childURL:
                        break
                    else:
                        url = childURL

            # Searches through links for image urls
            request = requests.Session()
            for link in pages:
                with request.get(link) as r:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    new = soup.find('div', {'class': 'pad-content-listing'})
                    brokenLinks = [image["src"] for image in new.findAll("img")]
                    for brokenLink in brokenLinks:
                        link = brokenLink.replace('.md.', '.').replace('.th.', '.')
                        links.append(link)
        linksDict = list(dict.fromkeys(links))

    except Exception as e:
        print(e)
        return None
    else:
        return linksDict


def gripeVideo(url):
    # extract direct video links from download page. This will likely break eventually.
    try:
        page = requests.get(url)
        data = page.text
        soup = BeautifulSoup(data, features="html5lib")

        for link in soup.find_all('a', {'class': 'btn btn-dl'}):
            suffix = link.get('href')
        return "https://share.dmca.gripe" + suffix
    except Exception as e:
        print(e)
        return None
