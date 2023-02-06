# `cyberdrop-dl`
**Bulk downloader for multiple file hosts** 

The latest version of the program is 3.6.58

<a href="https://www.buymeacoffee.com/juleswinnft" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

If you want to support me and my effort you can buy me a coffee or send me some crypto:

BTC: bc1qzw7l9d8ju2qnag3skfarrd0t5mkn0zyapnrcsn

ETH: 0xf36ef155C43Ed220BfBb2CBe9c5Ae172A8640e9B

XMR: 46vMP5MXVZqQeGzkA1mbX9WQKU8fbWRBJGAktDcjYkCMRDY7HMdLzi1DFsHCPLgms968cyUz1gCWVhy9cZir9Ae7M6anQ8Q

# Supported Sites

| Website          | Supported Link Types                                                                                                                                                                                                                   |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Anonfiles        | Download page: Anonfiles.com/...                                                                                                                                                                                                       |
| Bayfiles         | Download page: Bayfiles.com/...                                                                                                                                                                                                        |
| Bunkr            | Albums: bunkr.ru/a/... <br> Direct Videos: stream.bunkr.ru/v/... <br> Direct links: cdn.bunkr.ru/... <br> Direct links: i.bunkr.ru/... <br> Direct links: files.bunkr.ru/... <br> Direct links: media-files.bunkr.ru/...               |
| Coomer.party     | Profiles: coomer.party/... <br> Thumbnail Links: coomer.party/thumbnail/... <br> Data Links: coomer.party/data/... <br> coomer.party/.../post/...                                                                                      | 
| Cyberdrop        | Albums: cyberdrop.me/a/... <br> Direct Videos: fs-0#.cyberdrop.me/... <br> Direct Videos: f.cyberdrop.me/... <br> Direct Images: img-0#.cyberdrop.me/... <br> Direct Images: f.cyberdrop.me/... <br> Also works with .cc, .to, and .nl |
| Cyberfile        | folders: cyberfile.su/folder/... <br> shared: cyberfile.su/shared/... <br> Direct: cyberfile.su/...                                                                                                                                    | 
| Erome            | Albums: erome.com/a/...                                                                                                                                                                                                                |
| Fapello          | Models: fapello.com/...                                                                                                                                                                                                                |
| GoFile           | Albums: gofile.io/d/...                                                                                                                                                                                                                |
| HGameCG          | Albums: hgamecg.com/.../index.html                                                                                                                                                                                                     |
| ImgBox           | Albums: imgbox.com/g/... <br> Direct Images: images#.imgbox.com/... <br> Single Files: imgbox.com/...                                                                                                                                  |
| IMG.Kiwi         | Albums: img.kiwi/album/... <br> Direct Images: img.kiwi/image/... <br> User Profile: img.kiwi/#USER# <br> All User Albums: img.kiwi/#USER#/albums                                                                                      |
| jpg.fish         | Albums: jpg.fish/album/... <br> Direct Images: jpg.fish/image/... <br> User Profile: jpg.fish/#USER# <br> All User Albums: jpg.fish/#USER#/albums                                                                              |
| Kemono.party     | Profiles: kemono.party/... <br> Thumbnail Links: kemono.party/thumbnail/... <br> Data Links: kemono.party/data/... <br> kemono.party/.../post/...                                                                                      |
| LeakedNudes      | Thread: forum.leakednudes.co/threads/...  <br> Continue from (will download this post and after): forum.leakednudes.co/threads/...post-NUMBER                                                                                          |
| PixelDrain       | Albums: Pixeldrain.com/l/... <br> Single Files: Pixeldrain.com/u/...                                                                                                                                                                   |
| Pixl             | Albums: pixl.li/album/... <br> Direct Images: pixl.li/image/...  <br> User Profile: pixl.li/#USER# <br> All User Albums: pixl.li/#USER#/albums                                                                                         |
| Postimg.cc       | Albums: postimg.cc/gallery/... <br> Direct Images: postimg.cc/...                                                                                                                                                                      |
| rule34.xxx       | Direct Media (Image and Video): rule34.xxx/index.php?page=post&s=view&id=...                                                                                                                                                           |
| SimpCity         | Thread: simpcity.st/threads/...  <br> Continue from (will download this post and after): simpcity.st/threads/...post-NUMBER                                                                                                            | 
| SocialMediaGirls | Thread: forum.socialmediagirls.com/threads/...  <br> Continue from (will download this post and after): forum.socialmediagirls.com/threads/...post-NUMBER                                                                              |
| XBunkr           | Album: xbunkr.com/a/... <br> Direct Links: media.xbunkr.com/...                                                                                                                                                                        |

Reminder to leave the link full (include the https://)

# Information

**Requires Python 3.7 or higher (3.10 recommended)**

You can get Python from here: https://www.python.org/downloads/

Make sure you tick the check box for "Add python to path"
![alt text](https://simp2.jpg.church/PATHe426c23371048def.png)

Mac users will also likely need to open terminal and execute the following command: `xcode-select --install`

# Script Method
Go to the [releases page](https://github.com/Jules-WinnfieldX/CyberDropDownloader/releases) and download the Cyberdrop_DL.zip file. Extract it to wherever you want the program to be.

Put the links in the URLs.txt file then run `Start Windows.bat` (Windows) or `Start Mac.command` (OS X) or `Start Linux.sh` (Linux).

** Mac users will need to run the command `chmod +x 'Start Mac.command'` to make the file executable.

# CLI Method

Run `pip3 install cyberdrop-dl` in command prompt/terminal

Advanced users may want to use virtual environments (via `pipx`), but it's **NOT** required.

1. Run `cyberdrop-dl` once to generate an empty `URLs.txt` file.
2. Copy and paste your links into `URLs.txt`.
Each link you add has to go on its own line (paste link, press enter, repeat).
3. Run `cyberdrop-dl` again.
It will begin to download everything.
4. Enjoy!

## Arguments
If you know what you're doing, you can use the available options to adjust how the program runs.
```
$ cyberdrop-dl -h
usage: cyberdrop-dl [-h] [-V] [-i INPUT_FILE] [-o OUTPUT_FOLDER] [--log-file LOG_FILE] [--threads THREADS] [--attempts ATTEMPTS] [--include-id] [--exclude-videos] [--exclude-images] [--exclude-audio] [--exclude-other] [--ignore-history] [--thotsbay-username "USERNAME"] [--thotsbay-password "PASSWORD"] [--skip SITE] [link ...]

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
  --config-file             config file to read arguments from
  --threads THREADS         number of threads to use (0 = max)
  --attempts ATTEMPTS       number of attempts to download each file
  --connection-timeout      number of seconds to wait attempting to connect to a URL during the downloading phase
  --disable-attempt-limit   disables stopping the program based on attempt limits
  --include-id              include the ID in the download folder name
  --exclude-videos          exclude video files from downloading
  --exclude-images          exclude image files from downloading
  --exclude-audio           exclude audio files from downloading
  --exclude-other           exclude other files from downloading
  --ignore-history          ignores previous history and downloads everything
  --output-last-forum-post  Outputs the last post of a forum scrape to use as a starting point for future runs
  --proxy                   HTTP/HTTPS proxy used for downloading, format [protocal]://[ip]:[port]
  --separate-posts          Separates forum scraping into folders by post number
  --mark-downloaded         Sets the scraped files as downloaded without downloading
  --required-free-space     Required free space (in gigabytes) for the program to run
  --pixeldrain-api-key      api key for premium pixeldrain
  --xbunker-username        username to login to xbunker (only required if the thread requires it)
  --xbunker-password        password to login to xbunker (only required if the thread requires it)
  --socialmediagirls-username       username to login to socialmediagirls (only required if the thread requires it)
  --socialmediagirls-password       password to login to socialmediagirls (only required if the thread requires it)
  --simpcity-username       username to login to simpcity (only required if the thread requires it)
  --simpcity-password       password to login to simpcity (only required if the thread requires it)
  --jdownloader-enable      enables sending unsupported urls to a running jdownloader2 instance to download
  --jdownloader-username    username to login to jdownloader
  --jdownloader-password    password to login to jdownloader
  --jdownloader-device      device to login to for jdownloader
  --skip                    this removes the specified hosts links from downloads
  --ratelimit               this will add a ratelimiter to requests made in the program, the number you provide is in requests/second
  --throttle                this is a throttle between requests during the downloading phase, the number is in seconds
```
--skip can use: "anonfiles", "bunkr", "coomer.party", "cyberdrop", "cyberfile", "erome", "fapello", "gfycat",
        "gofile", "hgamecg", "imgbox", "img.kiwi", "jpg.fish", "pixeldrain", "pixl.li", "postimg.cc",
        "redgifs", "rule34", "saint", "socialmediagirls", "simpcity", "xbunker", "xbunkr"
