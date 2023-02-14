import logging

from myjdapi import myjdapi
from yarl import URL

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.error_classes import JDownloaderFailure


class JDownloader:
    """Class that handles connecting and passing links to JDownloader"""
    def __init__(self, jdownloader_args: dict, quiet: bool):
        self.jdownloader_device = jdownloader_args['jdownloader_device']
        self.jdownloader_username = jdownloader_args['jdownloader_username']
        self.jdownloader_password = jdownloader_args['jdownloader_password']

        self.jdownloader_enable = jdownloader_args['apply_jdownloader']
        self.jdownloader_agent = None
        self.quiet = quiet

    async def jdownloader_setup(self):
        """Setup function for JDownloader"""
        try:
            if not self.jdownloader_username or not self.jdownloader_password or not self.jdownloader_device:
                raise JDownloaderFailure("jdownloader credentials were not provided.")
            jd = myjdapi.Myjdapi()
            jd.set_app_key("CYBERDROP-DL")
            jd.connect(self.jdownloader_username, self.jdownloader_password)
            self.jdownloader_agent = jd.get_device(self.jdownloader_device)
        except JDownloaderFailure:
            await log("[red]Failed JDownloader setup[/red]", quiet=self.quiet)
            self.jdownloader_enable = False

    async def direct_unsupported_to_jdownloader(self, url: URL, title: str):
        """Sends links to JDownloader"""
        if self.jdownloader_enable:
            if not self.jdownloader_agent:
                await self.jdownloader_setup()
            try:
                if "facebook" in url.host.lower() or "instagram" in url.host.lower():
                    raise JDownloaderFailure("Blacklisted META")

                self.jdownloader_agent.linkgrabber.add_links([{
                    "autostart": False,
                    "links": str(url),
                    "packageName": title if title else "Cyberdrop-DL",
                    "overwritePackagizerRules": True
                    }])

            except JDownloaderFailure as e:
                logging.debug(e)
                await log("[red]Failed to send " + str(url) + " to JDownloader[/red]", quiet=self.quiet)
