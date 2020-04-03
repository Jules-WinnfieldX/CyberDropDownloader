#Cyberdrop Gallery Downloader Originally by nixxin
#Made better(?) by Jules--Winnfield

import requests
import os
import re
import json #test
import pathlib
from clint.textui import progress
from geturls import Extrair_Links
from multiprocessing import Pool
import multiprocessing
from time import sleep

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')
    
def download(passed_from_main):
    path = passed_from_main[0]
    item = passed_from_main[1]
    i=1
    try:
        while(True):
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
                    break
            except Exception as e:
                print(e)
                os.remove(path+str(filename))
                print("\nFailed attempt " + str(i)+ " for "+ filename +"\n")
                print("Retrying "+ filename + "...\n")
                i+=1
                
    except Exception as e:
        print(e)
        print()
        print()
        print("Failed to Download")
        print()
        print()
    else:
        print("Download of "+ filename +" Succesful")
        print()
            
if __name__ == '__main__':
    hearders = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}

    total = 0
    paths = pathlib.Path(__file__).parent.absolute()

    clear()

    if os.path.isfile("URLs.txt"):
        print("URLs.txt exists")
    else:
        f = open("URLs.txt", "w+");
        print("URLs.txt exists now")
        
    if os.stat("URLs.txt").st_size == 0:
        print("Please put URLs in URLs.txt");

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
        i = 0
        pass_to_func = []
        for link in links:
            pass_to_func.append([path, link])
            i += 1
            
        pool = Pool(processes = multiprocessing.cpu_count())
        proc = pool.map_async(download, pass_to_func)
        proc.wait()
                
    ex = input("Press enter to quit.")
