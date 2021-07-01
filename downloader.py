# Cyberdrop Gallery Downloader Originally by nixxin
# Made better(?) by Jules--Winnfield

import requests
import os
import re
import pathlib
from colorama import Fore, Style
from geturls import Extrair_Links
from multiprocessing import Pool
import multiprocessing


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
    attempts = 1
    try:
        while True:
            try:
                filename = _item[_item.rfind("/") + 1:]
                _url = _item

                if filename == "cyberdrop.me-downloaders":
                    break

                if os.path.isfile(_path + str(filename)):
                    log("           " + filename + " already exists.", Fore.LIGHTBLACK_EX)
                    break

                log("        Downloading " + filename + "...", Fore.LIGHTBLACK_EX)

                response = requests.get(_url, stream=True)
                incomingFileSize = int(response.headers['Content-length'])
                with open(_path + str(filename), "wb") as out_file:
                    for chunk in response.iter_content(chunk_size=50000):
                        if chunk:
                            out_file.write(chunk)
                del response
                if out_file:
                    storedFileSize = os.path.getsize(_path + str(filename))
                    if incomingFileSize == storedFileSize:
                        log("        Finished " + filename, Fore.GREEN)
                        break
                    else:
                        raise SizeError("File Size Specified: {} bytes, File Size Obtained: {} bytes".format(
                            incomingFileSize, storedFileSize), "These file sizes don't match")
            except Exception as e:
                log(e, Fore.RED)
                os.remove(_path + str(filename))
                log("        Failed attempt " + str(attempts) + " for " + filename, Fore.RED)
                log("        Retrying " + filename + "...", Fore.YELLOW)
                attempts += 1

    except Exception as e:
        print(e)
        print("Failed to Download")


if __name__ == '__main__':
    print("We are running 1")
    log("", Fore.RESET)
    print("We are running 2")
    headers = {'headers': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
    print("We are running 3")
    totalFiles = 0
    clear()

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

        html = requests.get(url, headers=headers)
        htmlAsText = html.text
        dirName = htmlAsText[htmlAsText.find("<title>") + 7:htmlAsText.find("</title>")]
        if 'cyberdrop' in url.lower():
            dirName = dirName.split("–")[0]
            dirName = dirName[7:-1]
            dirName = re.findall('^[^\[]*', dirName)
            dirName = dirName[0].rstrip()
        rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
        dirName = re.sub(rstr, "_", dirName)
        dirName += "/"
        path = './'+dirName

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
        if not (os.path.isdir(dirName)):
            try:
                os.mkdir(path)
                print()
                log("Created directory {dir}".format(dir=path), Fore.GREEN)
            except OSError as e:
                log("Creation of directory {dir} failed: {err}".format(dir=path, err=e), Fore.RED)
        print()

        pass_to_func = []
        for link in links:
            pass_to_func.append([path, link])

        print("Downloading " + str(len(pass_to_func)) + " files...")
        pool = Pool(processes=multiprocessing.cpu_count())
        proc = pool.map_async(download, pass_to_func)
        proc.wait()
        pool.close()

    exitText = input("\nFinished. Press enter to quit.")
