# `cyberdrop-dl`
**Bulk downloader for multiple file hosts**

# Supported Sites

| Website      | Supported Link Types                                                                                                                                                                                                                   |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Cyberdrop    | Albums: cyberdrop.me/a/... <br> Direct Videos: fs-0#.cyberdrop.me/... <br> Direct Videos: f.cyberdrop.me/... <br> Direct Images: img-0#.cyberdrop.me/... <br> Direct Images: f.cyberdrop.me/... <br> Also works with .cc, .to, and .nl |
| Putmega      | Albums: putmega.com/album/... <br> Direct Images: s#.putmega.com/... <br> Direct Images: putmega.com/image/... <br> User Profile: putmega.com/#USER# <br> All User Albums: putmega.com/#USER#/albums <br> Also works with putme.ga     |
| jpg.church   | Albums: jpg.church/album/... <br> Direct Images: jpg.church/image/... <br> User Profile: jpg.church/#USER# <br> All User Albums: jpg.church/#USER#/albums                                                                              |
| Pixl         | Albums: pixl.is/album/... <br> Direct Images: pixl.is/image/...  <br> User Profile: pixl.is/#USER# <br> All User Albums: pixl.is/#USER#/albums                                                                                         |
| Bunkr        | Albums: bunkr.is/a/... <br> Direct Videos: stream.bunkr.is/v/... <br> Direct Videos: cdn.bunkr.is/... <br> Direct Images: i.bunkr.is/... <br> Also works with Bunkr.to                                                                 |
| GoFile       | Albums: gofile.io/d/...                                                                                                                                                                                                                |
| Erome        | Albums: erome.com/a/...                                                                                                                                                                                                                |
| PixelDrain   | Albums: Pixeldrain.com/l/... <br> Single Files: Pixeldrain.com/u/...                                                                                                                                                                   |
| ThotsBay     | Thread: Thotsbay.com/threads/...  <br> Continue from (will download this post and after): Thotsbay.com/threads/...post-NUMBER                                                                                                          | 
| Anonfiles    | Download page: Anonfiles.com/...                                                                                                                                                                                                       | 
| Cyberfile.is | Folders: Cyberfile.is/folder/...                                                                                                                                                                                                       | 

Reminder to leave the link full (include the https://)

# Information

**Requires Python 3.7 or higher (3.10 recommended)**

You can get Python from here: https://www.python.org/downloads/

Make sure you tick the check box for "Add python to path"
![alt text](https://simp2.jpg.church/PATHe426c23371048def.png)

`cyberdrop-dl` will take the title of the archive and create a new folder for it, and download all of the available media to that folder.
It'll repeat that for every link you give it.

# Installation

## Manually
Go to the [releases page](https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases) and download the Cyberdrop_DL.zip file. Extract it to wherever you want the program to be.
## Using `pip`
Once Python is installed, run `pip3 install cyberdrop-dl`.

Advanced users may want to use virtual environments (via `pipx`), but it's **NOT** required.

# Usage

## Manual way (Manual install above)
Put the links in the URLs.txt file then run `Start Windows.bat` (Windows) or `Start Mac.command` (OS X) or `Start Linux.sh` (Linux).

** Mac users will need to run the command `chmod +x 'Start Mac.command'` to make the file executable.

## Simple (Pip install above)
1. Run `cyberdrop-dl` once to generate an empty `URLs.txt` file.
2. Copy and paste your links into `URLs.txt`.
Each link you add has to go on its own line (paste link, press enter, repeat).
3. Run `cyberdrop-dl` again.
It will begin to download everything.
4. Enjoy!

## Custom way (Pip install above)
If you know what you're doing, you can use some of the available options to adjust how the program runs.
```
$ cyberdrop-dl -h
usage: cyberdrop-dl [-h] [-V] [-i INPUT_FILE] [-o OUTPUT_FOLDER] [--log-file LOG_FILE] [--threads THREADS] [--attempts ATTEMPTS] [--include-id] [link ...]

Bulk downloader for multiple file hosts

positional arguments:
  link                  link to content to download (passing multiple links is supported)

optional arguments:
  -h, --help                show this help message and exit
  -V, --version             show program's version number and exit
  -i INPUT_FILE, --input-file INPUT_FILE             file containing links to download
  -o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER    folder to download files to
  --log-file LOG_FILE       log file to write to
  --db-file                 history DB file to write to
  --threads THREADS         number of threads to use (0 = max)
  --attempts ATTEMPTS       number of attempts to download each file
  --disable-attempt-limit   disables stopping the program based on attempt limits
  --include-id              include the ID in the download folder name
  --exclude-videos          exclude video files from downloading
  --exclude-images          exclude image files from downloading
  --exclude-audio           exclude audio files from downloading
  --exclude-other           exclude other files from downloading
  --ignore-history          ignores previous history and downloads everything
  --thotsbay-username       username to login to thotsbay (only required if the thread requires it)
  --thotsbay-password       password to login to thotsbay (only required if the thread requires it)
```

# Credit
The majority of the new download methodology came from alexdotis' [Chibisafe-Sharex-Scraper](https://github.com/alexdotis/Chibisafe-Sharex-Scraper).
Added to his code was the ability to take a more descriptive url object containing the album title, netloc and content urls. 
The download methodology now also checks for existing files. Simplified bunkr pairing to stop blank objects from being created and passed to the rest of the program.
