import requests
import os
from bs4 import BeautifulSoup, SoupStrainer


videoExtensions = ['.mp4', '.wmv', '.m4v']


def Extrair_Links(u):
    # Extract links from gallery
    try:
        # create request, and soup
        url = u
        page = requests.get(url)
        data = page.text
        soup = BeautifulSoup(data, features="html5lib")
        links = []
        # If cyberdrop, find id="file" href links
        if 'cyberdrop' in u.lower():
            for link in soup.find_all(id="file"):
                lis = link.get('href')
                if len(str(lis)) > 30:
                    lis = lis.replace('.nl/', '.cc/')
                    links.append(lis)
        # If dmca.gripe find 'a', {'class': 'download-button'} href links
        elif 'dmca.gripe' in u.lower():
            for link in soup.find_all('a', {'class': 'download-button'}):
                lis = link.get('href')
                if any(videoExtension in lis for videoExtension in videoExtensions):
                    # if it's a video, redo the process in gripeVideo
                    links.append(gripeVideo(lis))
                elif len(str(lis)) > 30:
                    links.append(lis)
        linksP = list(dict.fromkeys(links))
    except Exception as e:
        print(e)
        return None
    else:
        return linksP


def gripeVideo(u):
    # extract direct video links from download page. This will likely break eventually.
    try:
        url = u
        page = requests.get(url)
        data = page.text
        soup = BeautifulSoup(data, features="html5lib")

        for link in soup.find_all('a', {'class': 'btn btn-dl'}):
            lis = link.get('href')
        return "https://share.dmca.gripe" + lis
    except Exception as e:
        print(e)
        return None
