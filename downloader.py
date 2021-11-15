# Cyberdrop Gallery Downloader Originally by nixxin
# Made better(?) by Jules--Winnfield

import requests
import os
import re
import time
from colorama import Fore, Style
from geturls import Extrair_Links
from multiprocessing import Pool
from bs4 import BeautifulSoup
import multiprocessing
import settings


class SizeError(Exception):
    """Exception raised for errors in the input.
    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def log(text, style):
    # Log function for printing to command line
    print(style + str(text) + Style.RESET_ALL)


def clear():
    # Clears command window
    os.system('cls' if os.name == 'nt' else 'clear')


def download(passed_from_main):
    _path = passed_from_main[0]
    _referer = bytes(passed_from_main[1], "utf-8")
    _item = passed_from_main[2]
    _timeout = passed_from_main[3]

    attempts = 1
    allowed_attempts = (settings.file_attempts + 1) if settings.file_attempts != 0 else 0

    try:
        while True:
            filename = _item[_item.rfind("/") + 1:]
            temp_filename = f'{filename}.download'
            _url = _item

            if allowed_attempts != 0 and attempts >= allowed_attempts:
                log("\tHit user specified attempt limit" + " for " + filename + " skipping file", Fore.RED)
                break

            else:
                if attempts != 1:
                    log("\tRetrying " + filename + "...", Fore.YELLOW)
                try:
                    if filename == "cyberdrop.me-downloaders":
                        break

                    headers = {'referer': _referer}
                    resume = False

                    if not resume and os.path.isfile(_path + str(filename)):
                        log("\t" + filename + " already exists.", Fore.GREEN)
                        break

                    stored_file_size = None
                    if os.path.isfile(_path + str(temp_filename)):
                        stored_file_size = os.path.getsize(_path + str(temp_filename))
                        log("\t" + filename + f" already exists (partial, {stored_file_size} B).", Fore.LIGHTBLACK_EX)
                        headers['Range'] = f'bytes={stored_file_size}-'
                        resume = True

                    log("\tDownloading " + filename + "...", Fore.LIGHTBLACK_EX)

                    try:
                        response = requests.get(_url, stream=True, timeout=_timeout, headers=headers)
                        response.raise_for_status()
                        incoming_file_size = int(response.headers['Content-length'])
                        with open(_path + str(temp_filename), "ab" if resume else "wb") as out_file:
                            for chunk in response.iter_content(chunk_size=50000):
                                if chunk:
                                    out_file.write(chunk)
                    except requests.exceptions.HTTPError as err:
                        log("\t"+str(err), Fore.RED)

                        if response.status_code == 429:
                            time_to_sleep = response.headers['Retry-after']
                            log("\tFailed attempt {} for {}. Sleeping thread for {} seconds.".format(attempts, filename, time_to_sleep))
                            time.sleep(time_to_sleep)
                        else:
                            log("\tFailed attempt {} for {}.".format(attempts, filename), Fore.RED)
                        attempts += 1
                        continue

                    if os.path.isfile(_path + str(temp_filename)):
                        total_file_size = incoming_file_size if stored_file_size is None else (
                                        incoming_file_size + stored_file_size)
                        stored_file_size = os.path.getsize(_path + str(temp_filename))
                        if total_file_size == stored_file_size:
                            os.rename(_path + str(temp_filename), _path + str(filename))
                            log("\tFinished " + filename, Fore.GREEN)
                            break
                        else:
                            raise SizeError("File Size Specified: {} bytes, File Size Obtained: {} bytes".format(
                                total_file_size, stored_file_size), "These file sizes don't match")
                    else:
                        log("\tSomething went wrong" + " for " + filename, Fore.RED)
                        attempts += 1
                except Exception as e:
                    log(e, Fore.RED)
                    log("\tFailed attempt " + str(attempts) + " for " + filename, Fore.RED)
                    attempts += 1

    except Exception as e:
        print(e)
        print("Failed to Download")


if __name__ == '__main__':
    log("", Fore.RESET)

    response = requests.get("https://api.github.com/repos/Jules-WinnfieldX/CyberDropDownloader/releases/latest")
    latest_version = response.json()["tag_name"]
    current_version = "1.5.4"

    clear()

    if latest_version != current_version:
        log("A new version of CyberDropDownloader is available\n"
            "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n", Fore.RED)
        input("To continue anyways press enter")

    headers = {'headers': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}

    cpu_count = settings.threads if settings.threads != 0 else multiprocessing.cpu_count()
    download_folder = settings.download_folder
    timeout = settings.timeout

    if download_folder == "./Downloads/":
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
    else:
        if not os.path.exists(download_folder):
            log("The download folder specified (" + download_folder + ") does not exist ", Fore.RED)

    if os.path.isfile("URLs.txt"):
        print("URLs.txt exists")
    else:
        f = open("URLs.txt", "w+")
        print("URLs.txt created")

    if os.stat("URLs.txt").st_size == 0:
        print("Please put URLs in URLs.txt")

    file_object = open("URLs.txt", "r")
    for line in file_object:
        url = line.rstrip()

        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")

        try:
            if 'cyberdrop' in url.lower():
                directory_name = soup.select('h1.has-text-centered')[0].text.strip()
                directory_name = directory_name.split("–")[0]

            elif 'putme.ga' in url.lower() or 'pixl' in url.lower():
                directory_name = soup.find("meta", {"property": "og:title"}).attrs['content']

            elif 'bunk' in url.lower():
                directory_name = soup.select('h1.title')[0].text.strip()
                # Artificial limit to bypass rate limitting
                cpu_count = cpu_count if cpu_count < 3 else 2
        except:
            print("Skipping URL: {}".format(url))
            print("Please check the URL and if it's valid please create a github issue.")
            continue

        rstr = r"[\/\\\:\*\?\"\<\>\|\.]"  # '/ \ : * ? " < > | .'
        directory_name = re.sub(rstr, "_", directory_name)
        directory_name += "/"
        path = download_folder+directory_name

        print("\n======================================================\n")

        print("\nCollecting file links from " + url + "...")
        links = Extrair_Links(url)
        links = {k: v for k, v in links.items() if v is not None}

        if not links:
            print()
            input(url + " Couldn't find pictures.")
            exit()

        print()
        print("\tURL\t" + url)
        print("\tDIR\t" + path)
        print()
        if not (os.path.isdir(path)):
            try:
                os.mkdir(path)
                print()
                log("Created directory {dir}".format(dir=path), Fore.GREEN)
            except OSError as e:
                log("Creation of directory {dir} failed: {err}".format(dir=path, err=e), Fore.RED)
        print()

        pass_to_func = []
        for referer, link_list in links.items():
            for link in link_list:
                pass_to_func.append([path, referer, link, timeout])

        print("Downloading " + str(len(pass_to_func)) + " files...")
        pool = Pool(processes=cpu_count)
        proc = pool.map_async(download, pass_to_func)
        proc.wait()
        pool.close()

    exitText = input("\nFinished. Press enter to quit.")
