# CyberDropDownloader
**Bulk Gallery Downloader for Cyberdrop.me**

# Supported Sites

| Website | Supported Link Types |
| ------------- | ------------- |
| Cyberdrop  | Albums: cyberdrop.me/a/... <br> Direct Videos: fs-0#.cyberdrop.cc <br> Direct Images: img-0#.cyberdrop.to|
| Putmega | Albums: putmega.com/album/... <br> Direct Images: putmega.com/image/... <br> User Profile: putmega.com/#USER# <br> All User Albums: putmega.com/#USER#/albums |
| Pixl | Albums: pixl.is/album/... <br> Direct Images: pixl.is/image/... <br> User Profile: pixl.is/#USER# <br> All User Albums: pixl.is/#USER#/albums |
| Bunkr | Albums: bunkr.is/a/... <br> Direct Videos: stream.bunkr.is/v/... <br> Direct Videos: cdn.bunkr.is/... <br> Direct Images: i.bunkr.is/... |
| GoFile | Albums: gofile.io/d/... |

GoFile Requires Chrome to be installed on the system

~~DMCA.Gripe~~ (It's dead)

# Information

Created Using Python 3.9.6 (**Requires Python 3.6 or higher**)
https://www.python.org/downloads/release/python-396/

The program will take the title of the archive and create a new folder for it, and download all of the avilable media to that folder. It'll repeat for every link you have in URLs.txt.

# Installation

Download a release from https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases
Extract all of the files to a single directory.

**MAC**

https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg

Use this installer to install python

**PC**

https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe

Use this installer to install python, make sure you select the box that says "ADD TO PATH"

**Arch Linux** (Not maintained by me)

There is a package on the AUR named [`cyberdropdownloader-bin`](https://aur.archlinux.org/packages/cyberdropdownloader-bin/).

This can be installed using your preferred AUR helper with a command like `paru -Sy cyberdropdownloader-bin`. You can then run the program by running `$ cyberdrop-downloader`. This will create a `URLS.txt` file in your current path which you can populate to proceed with your downloads.

# Usage
Copy and paste links into URLs.txt. 
Each link you add has to go on it's own line. (paste link, press enter, repeat).

Double click on Start.bat (or Start.sh for Mac OS/Linux), it will download the needed libraries using PIP and run the program.

NOTE: Mac OS X / Linux users will likely have to run the command "chmod +x Start.sh" before they can execute the script.

# Credit

The majority of the new download methodology came from alexdotis' [Chibisafe-Sharex-Scraper](https://github.com/alexdotis/Chibisafe-Sharex-Scraper).
Added to his code was the ability to take a more descriptive url object containing the album title, netloc and content urls. 
The download methodology now also checks for existing files. Simplified bunkr pairing to stop blank objects from being created and passed to the rest of the program.
