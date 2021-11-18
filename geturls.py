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
    url += "/?sort=date_asc&page=1"
    links = {base_URL: None}

    while True:
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'html.parser')
        # Get image links
        html_filter = soup.find('div', {'class': 'pad-content-listing'})
        broken_links = [image["src"] for image in html_filter.findAll("img")]
        for brokenLink in broken_links:
            final_link = brokenLink.replace('.md.', '.').replace('.th.', '.')
            if url in links:
                if isinstance(links[url], list):
                    links[url].append(final_link)
            else:
                links[url] = [final_link]
        
        # Searches for next page link
        next_page = soup.find("li", {'class': 'pagination-next'})
        if next_page is None:
            return links
        else:
            for child in next_page.children:
                child_URL = child.get("href")
                if child_URL:
                    url = child_URL
                else:
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

        elif 'dmca.gripe' in base_URL.lower():
            links = dmca_gripe_extractor(soup, base_URL)

        elif 'putme.ga' in base_URL.lower() or 'pixl' in base_URL.lower():
            links = multi_page_extractor(soup, base_URL)

    except Exception as e:
        print(e)
        return None
    else:
        return links
