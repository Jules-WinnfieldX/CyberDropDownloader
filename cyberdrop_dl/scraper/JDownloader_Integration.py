from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Dict

from myjdapi import myjdapi

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.error_classes import JDownloaderFailure

if TYPE_CHECKING:
    from yarl import URL


class JDownloader:
    """Class that handles connecting and passing links to JDownloader"""
    def __init__(self, jdownloader_args: Dict, quiet: bool):
        self.jdownloader_device = jdownloader_args['jdownloader_device']
        self.jdownloader_username = jdownloader_args['jdownloader_username']
        self.jdownloader_password = jdownloader_args['jdownloader_password']
        self.jdownloader_enable = jdownloader_args['apply_jdownloader']
        self.quiet = quiet
        self.jdownloader_agent = self.jdownloader_setup()

    def jdownloader_setup(self) -> Optional[myjdapi.Jddevice]:
        """Setup function for JDownloader"""
        if not self.jdownloader_enable:
            return None

        try:
            if not self.jdownloader_username or not self.jdownloader_password or not self.jdownloader_device:
                raise JDownloaderFailure("jdownloader credentials were not provided.")
            jd = myjdapi.Myjdapi()
            jd.set_app_key("CYBERDROP-DL")
            jd.connect(self.jdownloader_username, self.jdownloader_password)
            return jd.get_device(self.jdownloader_device)
        except (myjdapi.MYJDApiException, JDownloaderFailure) as e:
            log("Failed JDownloader setup", quiet=self.quiet, style="red")
            self.jdownloader_enable = False
            return None

    async def direct_unsupported_to_jdownloader(self, url: URL, title: str) -> None:
        """Sends links to JDownloader"""
        if self.jdownloader_enable:
            try:
                assert url.host is not None
                if "facebook" in url.host.lower() or "instagram" in url.host.lower():
                    raise JDownloaderFailure("Blacklisted META")
                assert self.jdownloader_agent is not None
                self.jdownloader_agent.linkgrabber.add_links([{
                    "autostart": False,
                    "links": str(url),
                    "packageName": title if title else "Cyberdrop-DL",
                    "overwritePackagizerRules": True
                    }])

            except (JDownloaderFailure, AssertionError) as e:
                logging.debug(e)
                log(f"Failed to send {url} to JDownloader", quiet=self.quiet, style="red")
