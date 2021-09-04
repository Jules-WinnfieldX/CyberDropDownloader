# Cyberdrop Gallery Downloader Originally by nixxin
# Made better(?) by Jules--Winnfield

import requests
import os
import re
from colorama import Fore, Style
from geturls import Extrair_Links
from multiprocessing import Pool
from bs4 import BeautifulSoup, SoupStrainer
import multiprocessing
import settings


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class SizeError(Error):
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
    _item = passed_from_main[1]
    _timeout = passed_from_main[2]
    attempts = 1
    attemptsToTry = (settings.file_attempts + 1) if settings.file_attempts != 0 else 0
    try:
        while True:
            filename = _item[_item.rfind("/") + 1:]
            filenameTemp = f'{filename}.download'
            _url = _item

            if attemptsToTry != 0 and attempts >= attemptsToTry:
                log("        Hit user specified attempt limit" + " for " + filename + " skipping file", Fore.RED)
                break
            else:
                if attempts != 1:
                    log("        Retrying " + filename + "...", Fore.YELLOW)
                try:
                    if filename == "cyberdrop.me-downloaders":
                        break

                    headers = {}
                    resume = False

                    if not resume and os.path.isfile(_path + str(filename)):
                        log("           " + filename + " already exists.", Fore.LIGHTBLACK_EX)
                        break

                    storedFileSize = None
                    if os.path.isfile(_path + str(filenameTemp)):
                        storedFileSize = os.path.getsize(_path + str(filenameTemp))
                        log("           " + filename + f" already exists (partial, {storedFileSize} B).", Fore.LIGHTBLACK_EX)
                        headers['Range'] = f'bytes={storedFileSize}-'
                        resume = True

                    response = requests.get(_url, stream=True, timeout=_timeout, headers=headers)
                    incomingFileSize = int(response.headers['Content-length'])

                    log("        Downloading " + filename + "...", Fore.LIGHTBLACK_EX)

                    with open(_path + str(filenameTemp), "ab" if resume else "wb") as out_file:
                        for chunk in response.iter_content(chunk_size=50000):
                            if chunk:
                                out_file.write(chunk)
                    del response
                    if os.path.isfile(_path + str(filenameTemp)):
                        totalFileSize = incomingFileSize if storedFileSize is None else (
                                        incomingFileSize + storedFileSize)
                        storedFileSize = os.path.getsize(_path + str(filenameTemp))
                        if totalFileSize == storedFileSize:
                            os.rename(_path + str(filenameTemp), _path + str(filename))
                            log("        Finished " + filename, Fore.GREEN)
                            break
                        else:
                            raise SizeError("File Size Specified: {} bytes, File Size Obtained: {} bytes".format(
                                totalFileSize, storedFileSize), "These file sizes don't match")
                    else:
                        log("        Something went wrong" + " for " + filename, Fore.RED)
                        attempts += 1
                except Exception as e:
                    log(e, Fore.RED)
                    log("        Failed attempt " + str(attempts) + " for " + filename, Fore.RED)
                    attempts += 1

    except Exception as e:
        print(e)
        print("Failed to Download")


if __name__ == '__main__':
    log("", Fore.RESET)

    response = requests.get("https://api.github.com/repos/Jules-WinnfieldX/CyberDropDownloader/releases/latest")
    latestVersion = response.json()["tag_name"]
    currentVersion = "1.3.2"

    clear()

    if latestVersion != currentVersion:
        print("A new version of CyberDropDownloader is available\n"
              "Download it here: https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases/latest\n")

    headers = {'headers': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}

    cpu_count = settings.threads if settings.threads != 0 else multiprocessing.cpu_count()
    downloadFolder = settings.download_folder
    timeout = settings.timeout

    if downloadFolder == "./Downloads/":
        if not os.path.exists(downloadFolder):
            os.makedirs(downloadFolder)
    else:
        if not os.path.exists(downloadFolder):
            log("The download folder specified (" + downloadFolder + ") does not exist ", Fore.RED)

    totalFiles = 0

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

        if 'cyberdrop' in url.lower():
            dirName = soup.select('h1.has-text-centered')[0].text.strip()
            print(dirName)
            dirName = dirName.split("–")[0]
            dirName = re.findall('^[^\[]*', dirName)
            dirName = dirName[0].rstrip()

        elif 'putme.ga' or 'pixl' in url.lower():
            dirName = soup.find("meta", {"property": "og:title"}).attrs['content']

        elif 'bunk' in url.lower():
            dirName = soup.select('h1.title')[0].text.strip()

        rstr = r"[\/\\\:\*\?\"\<\>\|\.]"  # '/ \ : * ? " < > | .'
        dirName = re.sub(rstr, "_", dirName)
        dirName += "/"
        path = downloadFolder+dirName

        print("\n======================================================\n")

        print("\nCollecting file links from " + url + "...")
        links = Extrair_Links(url)

        if links is None:
            print()
            input(url + " Couldn't find pictures.")
            exit()

        print()
        print("       URL       " + url)
        print("       DIR       " + path)
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
        for link in links:
            pass_to_func.append([path, link, timeout])

        print("Downloading " + str(len(pass_to_func)) + " files...")
        pool = Pool(processes=cpu_count)
        proc = pool.map_async(download, pass_to_func)
        proc.wait()
        pool.close()

    exitText = input("\nFinished. Press enter to quit.")
