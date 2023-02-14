# `cyberdrop-dl`
**Bulk downloader for multiple file hosts** 

The latest version of the program is 4.0.5

Brand new and improved! Cyberdrop-DL now has an updated paint job, fantastic new look. On top of this it also downloads from different domains simultaneously.

# Support Cyberdrop-DL Development

<a href="https://www.buymeacoffee.com/juleswinnft" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

If you want to support me and my effort you can buy me a coffee or send me some crypto:

BTC: bc1qzw7l9d8ju2qnag3skfarrd0t5mkn0zyapnrcsn

ETH: 0xf36ef155C43Ed220BfBb2CBe9c5Ae172A8640e9B

XMR: 46vMP5MXVZqQeGzkA1mbX9WQKU8fbWRBJGAktDcjYkCMRDY7HMdLzi1DFsHCPLgms968cyUz1gCWVhy9cZir9Ae7M6anQ8Q

# More Information

Read the Wiki!

https://github.com/Jules-WinnfieldX/CyberDropDownloader/wiki/

# Supported Sites

| Website                 | Supported Link Types                                                                                                                                                                                                                   |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Anonfiles               | Download page: Anonfiles.com/...                                                                                                                                                                                                       |
| Bayfiles                | Download page: Bayfiles.com/...                                                                                                                                                                                                        |
| Bunkr                   | Albums: bunkr.ru/a/... <br> Direct Videos: stream.bunkr.ru/v/... <br> Direct links: cdn.bunkr.ru/... <br> Direct links: i.bunkr.ru/... <br> Direct links: files.bunkr.ru/... <br> Direct links: media-files.bunkr.ru/...               |
| Coomer.party            | Profiles: coomer.party/... <br> Thumbnail Links: coomer.party/thumbnail/... <br> Data Links: coomer.party/data/... <br> coomer.party/.../post/...                                                                                      | 
| Cyberdrop               | Albums: cyberdrop.me/a/... <br> Direct Videos: fs-0#.cyberdrop.me/... <br> Direct Videos: f.cyberdrop.me/... <br> Direct Images: img-0#.cyberdrop.me/... <br> Direct Images: f.cyberdrop.me/... <br> Also works with .cc, .to, and .nl |
| Cyberfile               | folders: cyberfile.su/folder/... <br> shared: cyberfile.su/shared/... <br> Direct: cyberfile.su/...                                                                                                                                    | 
| E-Hentai                | Albums: e-hentai.org/g/... <br> Posts: e-hentai.org/s/...                                                                                                                                                                              |
| Erome                   | Albums: erome.com/a/...                                                                                                                                                                                                                |
| Fapello                 | Models: fapello.com/...                                                                                                                                                                                                                |
| GoFile                  | Albums: gofile.io/d/...                                                                                                                                                                                                                |
| Gfycat                  | Gif: gfycat.com/...                                                                                                                                                                                                                    |
| HGameCG                 | Albums: hgamecg.com/.../index.html                                                                                                                                                                                                     |
| ImgBox                  | Albums: imgbox.com/g/... <br> Direct Images: images#.imgbox.com/... <br> Single Files: imgbox.com/...                                                                                                                                  |
| IMG.Kiwi                | Albums: img.kiwi/album/... <br> Direct Images: img.kiwi/image/... <br> User Profile: img.kiwi/#USER# <br> All User Albums: img.kiwi/#USER#/albums                                                                                      |
| jpg.church<br/>jpg.fish | Albums: jpg.church/album/... <br> Direct Images: jpg.church/image/... <br> User Profile: jpg.church/#USER# <br> All User Albums: jpg.church/#USER#/albums                                                                              |
| LoveFap                 | Albums: lovefap.com/a/... <br> Direct Images: s*.lovefap.com/content/photos/... <br> Videos: lovefap.com/video/...                                                                                                                     |
| NSFW.XXX                | Profile: nsfw.xxx/user/... <br> Post: nsfw.xxx/post/...                                                                                                                                                                                |
| PimpAndHost             | Albums: pimpandhost.com/album/... <br> Single Files: pimpandhost.com/image/...                                                                                                                                                         |
| PixelDrain              | Albums: Pixeldrain.com/l/... <br> Single Files: Pixeldrain.com/u/...                                                                                                                                                                   |
| Pixl                    | Albums: pixl.li/album/... <br> Direct Images: pixl.li/image/...  <br> User Profile: pixl.li/#USER# <br> All User Albums: pixl.li/#USER#/albums                                                                                         |
| Postimg.cc              | Albums: postimg.cc/gallery/... <br> Direct Images: postimg.cc/...                                                                                                                                                                      |
| SimpCity                | Thread: simpcity.st/threads/...  <br> Continue from (will download this post and after): simpcity.st/threads/...post-NUMBER                                                                                                            | 
| SocialMediaGirls        | Thread: forum.socialmediagirls.com/threads/...  <br> Continue from (will download this post and after): forum.socialmediagirls.com/threads/...post-NUMBER                                                                              |
| XBunker                 | Thread: xbunker.su/threads/...  <br> Continue from (will download this post and after): xbunker.su/threads/...post-NUMBER                                                                                                              |
| XBunkr                  | Album: xbunkr.com/a/... <br> Direct Links: media.xbunkr.com/...                                                                                                                                                                        |

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

## Arguments & Config
If you know what you're doing, you can use the available options to adjust how the program runs.

You can read more about all of these options [here](https://github.com/Jules-WinnfieldX/CyberDropDownloader/wiki/Config-Options). As they directly correlate with the config options.

```
$ cyberdrop-dl -h
usage: cyberdrop-dl [-h] [-V] [-i INPUT_FILE] [-o OUTPUT_FOLDER] [--log-file LOG_FILE] [--threads THREADS] [--attempts ATTEMPTS] [--include-id] [--exclude-videos] [--exclude-images] [--exclude-audio] [--exclude-other] [--ignore-history] [--simpcity-username "USERNAME"] [--simpcity-password "PASSWORD"] [--skip SITE] [link ...]

Bulk downloader for multiple file hosts

positional arguments:
  link                  link to content to download (passing multiple links is supported)

optional arguments:
-h, --help                                         show this help message and exit
-V, --version                                      show program's version number and exit
-i INPUT_FILE, --input-file INPUT_FILE             file containing links to download
-o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER    folder to download files to

--config-file 	                config file to read arguments from
--db-file 	                history database file to write to
--errored-urls-file             csv file to write failed download information to
--log-file 	                log file to write to
--output-last-forum-post-file 	text file to output last scraped post from a forum thread for re-feeding into CDL
--unsupported-urls-file 	csv file to output unsupported links into

--exclude-audio 	skip downloading of audio files
--exclude-images 	skip downloading of image files
--exclude-other 	skip downloading of images
--exclude-videos 	skip downloading of video files
--ignore-cache 	        ignores previous runs cached scrape history
--ignore-history 	ignores previous download history
--skip 	                removes host links from downloads

--allow-insecure-connections 	        allows insecure connections from content hosts
--attempts 	                        number of attempts to download each file
--block-sub-folders 	                block sub folders from being created
--disable-attempt-limit 	        disables the attempt limitation
--include-id 	                        include the ID in the download folder name
--skip-download-mark-completed 	        sets the scraped files as downloaded without downloading
--output-errored-urls 	                sets the failed urls to be output to the errored urls file
--output-unsupported-urls 	        sets the unsupported urls to be output to the unsupported urls file
--proxy 	                        HTTP/HTTPS proxy used for downloading, format [protocal]://[ip]:[port]
--remove-bunker-identifier 	        removes the bunkr added identifier from output filenames
--required-free-space 	                required free space (in gigabytes) for the program to run
--simultaneous-downloads-per-domain 	number of simultaneous downloads to use per domain

--sort-downloads 	sorts downloaded files after downloads have finished
--sort-directory 	folder to download files to
--sorted-audio 	        schema to sort audio
--sorted-images 	schema to sort images
--sorted-others 	schema to sort other
--sorted-videos 	schema to sort videos

--connection-timeout 	number of seconds to wait attempting to connect to a URL during the downloading phase
--ratelimit 	        this applies to requests made in the program during scraping, the number you provide is in requests/seconds
--throttle 	        this is a throttle between requests during the downloading phase, the number is in seconds

--output-last-forum-post 	outputs the last post of a forum scrape to use as a starting point for future runs
--separate-posts 	        separates forum scraping into folders by post number
	
--pixeldrain-api-key 	        api key for premium pixeldrain
--simpcity-password 	        password to login to simpcity
--simpcity-username 	        username to login to simpcity
--socialmediagirls-password 	password to login to socialmediagirls
--socialmediagirls-username 	username to login to socialmediagirls
--xbunker-password 	        password to login to xbunker
--xbunker-username 	        username to login to xbunker

--apply-jdownloader 	enables sending unsupported URLs to a running jdownloader2 instance to download
--jdownloader-username 	username to login to jdownloader
--jdownloader-password 	password to login to jdownloader
--jdownloader-device 	device name to login to for jdownloader

--dont-show-overall-progress 	removes overall progress section while downloading
--dont-show-forum-progress 	removes forum progress section while downloading
--dont-show-thread-progress 	removes thread progress section while downloading
--dont-show-domain-progress 	removes domain progress section while downloading
--dont-show-album-progress 	removes album progress section while downloading
--dont-show-file-progress 	removes file progress section while downloading

```

--skip-hosts can use: `"anonfiles", "bayfiles", "bunkr", "coomer.party", "cyberdrop", "cyberfile", "e-hentai", "erome", "fapello", "gfycat", "gofile", "hgamecg", "img.kiwi", "imgbox", "jpg.church", "jpg.fish", "kemono.party", "lovefap", "nsfw.xxx", "pimpandhost", "pixeldrain", "pixl.li", "postimg", "saint", "simpcity", "socialmediagirls", "xbunker", "xbunkr"`
