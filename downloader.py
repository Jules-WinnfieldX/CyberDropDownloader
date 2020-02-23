
#Cyberdrop Gallery Downloader Originally by nixxin
#Made better(?) by Jules--Winnfield

import requests
import os
import re
import json #test
import pathlib
from clint.textui import progress
from geturls import Extrair_Links

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

hearders = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}

total = 0
paths = pathlib.Path(__file__).parent.absolute()

clear()

file_object = open("URLs.txt", "r")
for line in file_object:
    url = line.rstrip()

    n = requests.get(url, headers=hearders)
    a1 = n.text
    di = a1[a1.find("<title>") + 7 : a1.find("</title>")]
    di = di.split("–")[0]
    di = di[7:-1]
    di = re.sub('[^\w\-_()\. ]', '_', di)
    di = di + "/"

    links = []
    print("Collecting file links from given URL...")
    links = Extrair_Links(url)

    if links == None:
        print()
        input(url + " Couldn't find pictures.")
        exit()
    else:
        for item in links:
            total = total + 1

    path = str(paths) + "/" + di
    print()
    print("       URL       " + url)
    print("       DIR       " + di)
    print()
    try:
        os.mkdir(path)
    except OSError:
        print ("Creation of directory %s failed" % path)
    else:
        print()
        print ("Directory %s was created" % path)
    print()

    total = int(total)
    for item in links:
        i=1
        try:
            sig = True
            while(sig):
                try:
                    print("Downloading " + item + " ...")
                    filename = item[item.rfind("/") + 1:]
                    url = item

                    if os.path.isfile(path+str(filename)):
                        print("File Already Exists")
                        break
                    
                    response = requests.get(url, stream=True)
                    with open(path+str(filename), "wb") as out_file:
                        for chunk in response.iter_content(chunk_size=None):
                            if chunk:
                                out_file.write(chunk)
                    del response
                    if out_file:
                        sig = False
                except Exception as e:
                    print(e)
                    os.remove(path+str(filename))
                    print("\nFailed attempt " + str(i)+"\n")
                    print("Retrying...\n")
                    i+=1
                    
        except Exception as e:
            print(e)
            print()
            print()
            print("Failed to Download")
            print()
            print()
        else:
            print("Download Succesful")
            print()
