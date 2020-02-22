# CyberDropDownloader
Bulk Gallery Downloader for Cyberdrop.me

Created Using Python 3.7.4
https://www.python.org/downloads/release/python-374/


So how do you use it?

Install Python
Make sure you add Python to path by clicking this box seen here: https://datatofish.com/wp-content/uploads/2018/10/0001_add_Python_to_Path.png

Make sure you do the full installation, not a custom installation.

If you already have a similar version of python installed, make sure you have pip installed.

Download a copy of the reposity, you will see 5 files: downloader.py, geturls.py, requirements.txt, start.bat, and URLs.txt
You can read over any of the source code and see what is happening.

Now is where it get's easy. Any time you find a Cyberdrop.me archive you want to download, you copy the link, and put it in URLs.txt. 
Each link you add has to go on it's own line. (paste link, press enter, repeat). Make sure to save the file.

Double click on start.bat, it will download the needed libraries using PIP and run the program.

If the program errors out the first time before anything happens, that's normal. Just close the window and start it again.




Common Issues:

ModuleNotFoundError: No module named 'requests'
For some reason, when you ran the start.bat file, it didn't work as intended. Open command prompt, and navigate to the folder containing the files using CD, and type the following: "pip install -r requirements.txt"
