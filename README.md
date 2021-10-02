# CyberDropDownloader
**Bulk Gallery Downloader for Cyberdrop.me**

# Supported Sites
Cyberdrop.me

DMCA.Gripe

Putmega

Pixl

Bunkr.to

# Information

Created Using Python 3.7.4
https://www.python.org/downloads/release/python-374/

The program will take the title of the archive and create a new folder for it, and download all of the images to that folder. It'll repeat for every link you have in URLs.txt.
If there are no links in URLs.txt, it will instantly close and nothing will happen.

# Installation

Download a release from https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases
Extract all of the files to a single directory.

**MAC**

https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg

Use this installer to install python

**PC**

https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe

Use this installer to install python, make sure you select the box that says "ADD TO PATH"

**Arch Linux**

There is a package on the AUR named [`cyberdropdownloader-bin`](https://aur.archlinux.org/packages/cyberdropdownloader-bin/).

This can be installed using your preffered AUR helper with a command like `paru -Sy cyberdropdownloader-bin`. You can then run the program by running `$ cyberdrop-downloader`. This will create a `URLS.txt` file in your current path which you can populate to proceed with your downloads.

# Usage
Copy and paste links into URLs.txt. 
Each link you add has to go on it's own line. (paste link, press enter, repeat).

Double click on Start.bat (or Start.sh for Mac OS/Linux), it will download the needed libraries using PIP and run the program.

NOTE: Mac OS X / Linux users will likely have to run the command "chmod +x Start.sh" before they can execute the script.
