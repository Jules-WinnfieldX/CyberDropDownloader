import requests
from bs4 import BeautifulSoup

video_extensions = ['.mp4', '.wmv', '.m4v', '.mov']


def cyberdrop_extractor(soup, base_URL):
    links = {base_URL: None}
    if 'cyberdrop' in base_URL.lower():
        for link in soup.find_all(id="file"):
            final_link = link.get('href')
            if len(str(final_link)) > 30:
                final_link = final_link.replace('.nl/', '.cc/')
                if isinstance(links[base_URL], list):
                    links[base_URL].append(final_link)
                else:
                    links[base_URL] = [final_link]
    return links


def bunkr_extractor(soup, base_URL):
    links = {base_URL: None}
    for link in soup.find_all(class_="image"):
        final_link = link.get('href')
        if any(video_extension in final_link.lower() for video_extension in video_extensions):
            new_base_URL = final_link.replace('https://cdn.bunkr.is/', 'https://stream.bunkr.is/v/')
            final_link = final_link.replace('https://cdn.bunkr.is/', 'https://stream.bunkr.is/d/')
            if new_base_URL in links:
                links[new_base_URL].append(final_link)
            else:
                links[new_base_URL] = [final_link]
            continue
        if isinstance(links[base_URL], list):
            links[base_URL].append(final_link)
        else:
            links[base_URL] = [final_link]
    return links


def dmca_gripe_extractor(soup, base_URL):
    links = {base_URL: None}
    for link in soup.find_all('a', {'class': 'download-button'}):
        potential_final_link = link.get('href')
        if any(videoExtension in potential_final_link.lower() for videoExtension in video_extensions):
            # extract direct video links from download page. This will likely break eventually.
            try:
                page = requests.get(potential_final_link)
                data = page.text
                soup = BeautifulSoup(data, features="html5lib")

                for link in soup.find_all('a', {'class': 'btn btn-dl'}):
                    suffix = link.get('href')
                if isinstance(links[potential_final_link], list):
                    links[potential_final_link].append("https://share.dmca.gripe" + suffix)
                else:
                    links[potential_final_link] = ["https://share.dmca.gripe" + suffix]
            except Exception as e:
                print(e)
                return None
        elif len(str(potential_final_link)) > 30:
            if isinstance(links[base_URL], list):
                links[base_URL].append(potential_final_link)
            else:
                links[base_URL] = [potential_final_link]
    return links


def multi_page_extractor(soup, base_URL):
    # First correct any 'bad' URLs by getting the real embedded url from the page itself
    url = soup.find(attrs={"data-text": "album-name"}).get('href')
    pages = [url]
    links = {base_URL: None}

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
            broken_links = [image["src"] for image in new.findAll("img")]
            for brokenLink in broken_links:
                final_link = brokenLink.replace('.md.', '.').replace('.th.', '.')
                if isinstance(links[link], list):
                    links[link].append(final_link)
                else:
                    links[link] = [final_link]
    return links


def Extrair_Links(base_URL):
    # Extract links from gallery
    try:
        page = requests.get(base_URL)
        data = page.text
        soup = BeautifulSoup(data, features="html5lib")
        links = {}

        if 'cyberdrop' in base_URL.lower():
            links = cyberdrop_extractor(soup, base_URL)

        elif 'bunkr' in base_URL.lower():
            links = bunkr_extractor(soup, base_URL)

        # If dmca.gripe find 'a', {'class': 'download-button'} href links
        elif 'dmca.gripe' in base_URL.lower():
            links = dmca_gripe_extractor(soup, base_URL)

        # If putme.ga or pixl, correct any bad urls, find all pages in album,
        # find all image links and then correct all image links
        elif 'putme.ga' in base_URL.lower() or 'pixl' in base_URL.lower():
            links = multi_page_extractor(soup, base_URL)

    except Exception as e:
        print(e)
        return None
    else:
        return links
