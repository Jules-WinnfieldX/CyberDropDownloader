# CyberDropDownloader
**Bulk Gallery Downloader for Cyberdrop.me**

# Supported Sites

| Website    | Supported Link Types                                                                                                                                                                                                                   |
|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Cyberdrop  | Albums: cyberdrop.me/a/... <br> Direct Videos: fs-0#.cyberdrop.me/... <br> Direct Videos: f.cyberdrop.me/... <br> Direct Images: img-0#.cyberdrop.me/... <br> Direct Images: f.cyberdrop.me/... <br> Also works with .cc, .to, and .nl |
| Putmega    | Albums: putmega.com/album/... <br> Direct Images: s#.putmega.com/... <br> Direct Images: putmega.com/image/... <br> User Profile: putmega.com/#USER# <br> All User Albums: putmega.com/#USER#/albums <br> Also works with putme.ga     |
| jpg.church | Albums: jpg.church/album/... <br> Direct Images: jpg.church/image/... <br> User Profile: jpg.church/#USER# <br> All User Albums: jpg.church/#USER#/albums                                                                              |
| Pixl       | Albums: pixl.is/album/... <br> Direct Images: pixl.is/image/...  <br> User Profile: pixl.is/#USER# <br> All User Albums: pixl.is/#USER#/albums                                                                                         |
| Bunkr      | Albums: bunkr.is/a/... <br> Direct Videos: stream.bunkr.is/v/... <br> Direct Videos: cdn.bunkr.is/... <br> Direct Images: i.bunkr.is/... <br> Also works with Bunkr.to                                                                 |
| GoFile     | Albums: gofile.io/d/...                                                                                                                                                                                                                |
| Erome      | Albums: erome.com/a/...                                                                                                                                                                                                                
| PixelDrain | Albums: Pixeldrain.com/l/... <br> Single Files: Pixeldrain.com/u/...                                                                                                                                                                                                               

# Information

Created Using Python 3.9.6 (**Requires Python 3.7 or higher**)
https://www.python.org/downloads/release/python-396/

The program will take the title of the archive and create a new folder for it, and download all of the avilable media to that folder. It'll repeat for every link you have in URLs.txt.

# Installation

Download a release from https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases
Extract all of the files to a single directory.

## macOS

https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg

Use this installer to install python

## Windows

https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe

Use this installer to install python, make sure you select the box that says "ADD TO PATH"

## Arch Linux (Not maintained by me)

There is a package on the AUR named [`cyberdropdownloader-bin`](https://aur.archlinux.org/packages/cyberdropdownloader-bin/).

This can be installed using your preferred AUR helper with a command like `paru -Sy cyberdropdownloader-bin`. You can then run the program by running `cyberdrop-downloader`. This will create a `URLS.txt` file in your current path which you can populate to proceed with your downloads.

# Usage
Copy and paste links into `URLs.txt`. 
Each link you add has to go on it's own line. (paste link, press enter, repeat).

Double click on `Start.bat` (or `Start.sh` for macOS/Linux), it will download the needed libraries using pip and run the program.

NOTE: macOS and Linux users will likely have to make the start script executable (`chmod +x Start.sh`) before they can run the script.

# Credit

The majority of the new download methodology came from alexdotis' [Chibisafe-Sharex-Scraper](https://github.com/alexdotis/Chibisafe-Sharex-Scraper).
Added to his code was the ability to take a more descriptive url object containing the album title, netloc and content urls. 
The download methodology now also checks for existing files. Simplified bunkr pairing to stop blank objects from being created and passed to the rest of the program.
