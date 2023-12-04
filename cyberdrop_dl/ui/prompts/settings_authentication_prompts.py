from __future__ import annotations

from typing import TYPE_CHECKING

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console

from cyberdrop_dl.utils.args.browser_cookie_extraction import get_forum_cookies, get_ddos_guard_cookies
from cyberdrop_dl.managers.manager import Manager

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager

console = Console()


def edit_authentication_values_prompt(manager: Manager) -> None:
    """Edit the authentication values"""
    auth = manager.config_manager.authentication_data

    while True:
        console.clear()
        console.print("Editing Authentication Values")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Edit DDOS-Guard Cookies"),
                Choice(2, "Edit Forum Authentication Values"),
                Choice(3, "Edit JDownloader Authentication Values"),
                Choice(4, "Edit Reddit Authentication Values"),
                Choice(5, "Edit GoFile API Key"),
                Choice(6, "Edit Imgur Client ID"),
                Choice(7, "Edit PixelDrain API Key"),
                Choice(8, "Done"),
            ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
        ).execute()

        # Edit DDOS-Guard Cookies
        if action == 1:
            edit_ddos_guard_cookies_prompt(manager)

        # Edit Forums
        if action == 2:
            edit_forum_authentication_values_prompt(manager)

        # Edit JDownloader
        elif action == 3:
            edit_jdownloader_authentication_values_prompt(auth)

        # Edit Reddit
        elif action == 4:
            edit_reddit_authentication_values_prompt(auth)

        # Edit GoFile API Key
        elif action == 5:
            console.clear()
            gofile_api_key = inquirer.text(
                message="Enter the GoFile API Key:",
                default=auth["GoFile"]["gofile_api_key"],
                long_instruction="You can get your premium GoFile API Key from https://gofile.io/myProfile",
            ).execute()
            auth["GoFile"]["gofile_api_key"] = gofile_api_key

        # Edit Imgur Client ID
        elif action == 6:
            console.clear()
            imgur_client_id = inquirer.text(
                message="Enter the Imgur Client ID:",
                default=auth["Imgur"]["imgur_client_id"],
                long_instruction="You can create an app and get your client ID "
                                 "from https://imgur.com/account/settings/apps"
            ).execute()
            auth["Imgur"]["imgur_client_id"] = imgur_client_id

        # Edit PixelDrain API Key
        elif action == 7:
            console.clear()
            pixeldrain_api_key = inquirer.text(
                message="Enter the PixelDrain API Key:",
                default=auth["PixelDrain"]["pixeldrain_api_key"],
                long_instruction="You can get your premium API Key from https://pixeldrain.com/user/api_keys"
            ).execute()
            auth["PixelDrain"]["pixeldrain_api_key"] = pixeldrain_api_key

        # Done
        elif action == 8:
            manager.config_manager.write_updated_authentication_config()
            return


def edit_ddos_guard_cookies_prompt(manager: Manager) -> None:
    """Edit the forum authentication values"""
    while True:
        console.clear()
        console.print("Editing DDOS-Guard Cookie Values")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Browser Cookie Extraction"),
                Choice(2, "Enter Cookie Values Manually"),
                Choice(3, "Done"),
            ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
        ).execute()

        # Browser Cookie Extraction
        if action == 1:
            action = inquirer.select(
                message="Which browser should we load cookies from?",
                choices=[
                    Choice("chrome", "Chrome"),
                    Choice("firefox", "FireFox"),
                    Choice("edge", "Edge"),
                    Choice("safari", "Safari"),
                    Choice("opera", "Opera"),
                    Choice("brave", "Brave"),
                    Choice(1, "Done"),
                ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
            ).execute()

            # Done
            if action == 1:
                continue

            # Browser Selection
            if action == "chrome":
                get_ddos_guard_cookies(manager, "chrome")
            elif action == "firefox":
                get_ddos_guard_cookies(manager, "firefox")
            elif action == "edge":
                get_ddos_guard_cookies(manager, "edge")
            elif action == "safari":
                get_ddos_guard_cookies(manager, "safari")
            elif action == "opera":
                get_ddos_guard_cookies(manager, "opera")
            elif action == "brave":
                get_ddos_guard_cookies(manager, "brave")
            return

        # Enter Cookie Values Manually
        elif action == 2:
            bunkr_ddg1 = inquirer.text(
                message="Enter your DDG1 value for Bunkr:",
                default=manager.config_manager.authentication_data["DDOS-Guard"]["bunkrr_ddg1"],
            ).execute()
            bunkr_ddg2 = inquirer.text(
                message="Enter your DDG2 value for Bunkr:",
                default=manager.config_manager.authentication_data["DDOS-Guard"]["bunkrr_ddg2"],
            ).execute()
            bunkr_ddgid = inquirer.text(
                message="Enter your DDGID value for Bunkr:",
                default=manager.config_manager.authentication_data["DDOS-Guard"]["bunkrr_ddgid"],
            ).execute()

            coomer_ddg1 = inquirer.text(
                message="Enter your DDG1 value for Coomer:",
                default=manager.config_manager.authentication_data["DDOS-Guard"]["coomer_ddg1"],
            ).execute()
            kemono_ddg1 = inquirer.text(
                message="Enter your DDG1 value for Kemono:",
                default=manager.config_manager.authentication_data["DDOS-Guard"]["kemono_ddg1"],
            ).execute()

            manager.config_manager.authentication_data["DDOS-Guard"]["bunkr_ddg1"] = bunkr_ddg1
            manager.config_manager.authentication_data["DDOS-Guard"]["bunkr_ddg2"] = bunkr_ddg2
            manager.config_manager.authentication_data["DDOS-Guard"]["bunkr_ddgid"] = bunkr_ddgid
            manager.config_manager.authentication_data["DDOS-Guard"]["coomer_ddg1"] = coomer_ddg1
            manager.config_manager.authentication_data["DDOS-Guard"]["kemono_ddg1"] = kemono_ddg1

            return
        elif action == 3:
            return


def edit_forum_authentication_values_prompt(manager: Manager) -> None:
    """Edit the forum authentication values"""
    while True:
        console.clear()
        console.print("Editing Forum Authentication Values")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Browser Cookie Extraction"),
                Choice(2, "Enter Cookie Values Manually"),
                Choice(3, "Done"),
            ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
        ).execute()

        # Browser Cookie Extraction
        if action == 1:
            action = inquirer.select(
                message="Which browser should we load cookies from?",
                choices=[
                    Choice("chrome", "Chrome"),
                    Choice("firefox", "FireFox"),
                    Choice("edge", "Edge"),
                    Choice("safari", "Safari"),
                    Choice("opera", "Opera"),
                    Choice("brave", "Brave"),
                    Choice(1, "Done"),
                ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
            ).execute()

            # Done
            if action == 1:
                continue

            # Browser Selection
            if action == "chrome":
                get_forum_cookies(manager, "chrome")
            elif action == "firefox":
                get_forum_cookies(manager, "firefox")
            elif action == "edge":
                get_forum_cookies(manager, "edge")
            elif action == "safari":
                get_forum_cookies(manager, "safari")
            elif action == "opera":
                get_forum_cookies(manager, "opera")
            elif action == "brave":
                get_forum_cookies(manager, "brave")
            return

        # Enter Cookie Values Manually
        elif action == 2:
            celebforum_username = inquirer.text(
                message="Enter your CelebForum Username:",
                default=manager.config_manager.authentication_data["Forums"]["celebforum_username"],
            ).execute()
            celebforum_password = inquirer.text(
                message="Enter your CelebForum Password:",
                default=manager.config_manager.authentication_data["Forums"]["celebforum_password"],
            ).execute()

            f95zone_username = inquirer.text(
                message="Enter your F95Zone Username:",
                default=manager.config_manager.authentication_data["Forums"]["f95zone_username"],
            ).execute()
            f95zone_password = inquirer.text(
                message="Enter your F95Zone Password:",
                default=manager.config_manager.authentication_data["Forums"]["f95zone_password"],
            ).execute()

            leakedmodels_username = inquirer.text(
                message="Enter your LeakedModels Username:",
                default=manager.config_manager.authentication_data["Forums"]["leakedmodels_username"],
            ).execute()
            leakedmodels_password = inquirer.text(
                message="Enter your LeakedModels Password:",
                default=manager.config_manager.authentication_data["Forums"]["leakedmodels_password"],
            ).execute()

            nudostar_username = inquirer.text(
                message="Enter your NudoStar Username:",
                default=manager.config_manager.authentication_data["Forums"]["nudostar_username"],
            ).execute()
            nudostar_password = inquirer.text(
                message="Enter your NudoStar Password:",
                default=manager.config_manager.authentication_data["Forums"]["nudostar_password"],
            ).execute()

            simpcity_username = inquirer.text(
                message="Enter your SimpCity Username:",
                default=manager.config_manager.authentication_data["Forums"]["simpcity_username"],
            ).execute()
            simpcity_password = inquirer.text(
                message="Enter your SimpCity Password:",
                default=manager.config_manager.authentication_data["Forums"]["simpcity_password"],
            ).execute()

            socialmediagirls_username = inquirer.text(
                message="Enter your SocialMediaGirls Username:",
                default=manager.config_manager.authentication_data["Forums"]["socialmediagirls_username"],
            ).execute()
            socialmediagirls_password = inquirer.text(
                message="Enter your SocialMediaGirls Password:",
                default=manager.config_manager.authentication_data["Forums"]["socialmediagirls_password"],
            ).execute()

            xbunker_username = inquirer.text(
                message="Enter your XBunker Username:",
                default=manager.config_manager.authentication_data["Forums"]["xbunker_username"],
            ).execute()
            xbunker_password = inquirer.text(
                message="Enter your XBunker Password:",
                default=manager.config_manager.authentication_data["Forums"]["xbunker_password"],
            ).execute()

            manager.config_manager.authentication_data["Forums"]["celebforum_username"] = celebforum_username
            manager.config_manager.authentication_data["Forums"]["f95zone_username"] = f95zone_username
            manager.config_manager.authentication_data["Forums"]["leakedmodels_username"] = leakedmodels_username
            manager.config_manager.authentication_data["Forums"]["nudostar_username"] = nudostar_username
            manager.config_manager.authentication_data["Forums"]["simpcity_username"] = simpcity_username
            manager.config_manager.authentication_data["Forums"]["socialmediagirls_username"] = socialmediagirls_username
            manager.config_manager.authentication_data["Forums"]["xbunker_username"] = xbunker_username

            manager.config_manager.authentication_data["Forums"]["celebforum_password"] = celebforum_password
            manager.config_manager.authentication_data["Forums"]["f95zone_password"] = f95zone_password
            manager.config_manager.authentication_data["Forums"]["leakedmodels_password"] = leakedmodels_password
            manager.config_manager.authentication_data["Forums"]["nudostar_password"] = nudostar_password
            manager.config_manager.authentication_data["Forums"]["simpcity_password"] = simpcity_password
            manager.config_manager.authentication_data["Forums"]["socialmediagirls_password"] = socialmediagirls_password
            manager.config_manager.authentication_data["Forums"]["xbunker_password"] = xbunker_password
            return
        elif action == 3:
            return


def edit_jdownloader_authentication_values_prompt(auth: Dict) -> None:
    """Edit the JDownloader authentication values"""
    console.clear()
    jdownloader_username = inquirer.text(
        message="Enter the JDownloader Username:",
        default=auth["JDownloader"]["jdownloader_username"],
    ).execute()
    jdownloader_password = inquirer.text(
        message="Enter the JDownloader Password:",
        default=auth["JDownloader"]["jdownloader_password"],
    ).execute()
    jdownloader_device = inquirer.text(
        message="Enter the JDownloader Device Name:",
        default=auth["JDownloader"]["jdownloader_device"],
    ).execute()

    auth["JDownloader"]["jdownloader_username"] = jdownloader_username
    auth["JDownloader"]["jdownloader_password"] = jdownloader_password
    auth["JDownloader"]["jdownloader_device"] = jdownloader_device


def edit_reddit_authentication_values_prompt(auth: Dict) -> None:
    """Edit the reddit authentication values"""
    console.clear()
    console.print(
        "You can create a Reddit App to use here: https://www.reddit.com/prefs/apps/"
    )
    reddit_secret = inquirer.text(
        message="Enter the Reddit Secret value:",
        default=auth["Reddit"]["reddit_secret"],
    ).execute()
    reddit_personal_use_script = inquirer.text(
        message="Enter the Reddit Personal Use Script value:",
        default=auth["Reddit"]["reddit_personal_use_script"],
    ).execute()

    auth["Reddit"]["reddit_secret"] = reddit_secret
    auth["Reddit"]["reddit_personal_use_script"] = reddit_personal_use_script
