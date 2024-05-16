from __future__ import annotations

from typing import TYPE_CHECKING

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator
from rich.console import Console

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager

console = Console()


def edit_global_settings_prompt(manager: Manager) -> None:
    """Edit the authentication values"""
    while True:
        console.clear()
        console.print("Editing Global Settings")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Edit General Settings"),
                Choice(2, "Edit Rate Limiting Settings"),
                Choice(3, "Edit UI Options"),
                Choice(4, "Done"),
            ],
            vi_mode=manager.vi_mode,
        ).execute()

        # Edit General Settings
        if action == 1:
            edit_general_settings_prompt(manager)

        # Edit Rate Limiting Settings
        elif action == 2:
            edit_rate_limiting_settings_prompt(manager)
            
        # Edit UI Settings
        elif action == 3:
            edit_ui_settings_prompt(manager)

        # Done
        elif action == 4:
            manager.config_manager.write_updated_global_settings_config()
            break


def edit_general_settings_prompt(manager: Manager) -> None:
    """Edit the general settings"""
    console.clear()
    console.print("Editing General Settings")
    allow_insecure_connections = inquirer.confirm("Allow insecure connections?", vi_mode=manager.vi_mode).execute()
    user_agent = inquirer.text(
        message="User Agent:",
        default=manager.config_manager.global_settings_data['General']['user_agent'],
        validate=EmptyInputValidator("Input should not be empty"),
        vi_mode=manager.vi_mode,
    ).execute()
    proxy = inquirer.text(
        message="Proxy:",
        default=manager.config_manager.global_settings_data['General']['proxy'],
        vi_mode=manager.vi_mode,
    ).execute()
    flaresolverr = inquirer.text(
        message="FlareSolverr (IP:PORT):",
        default=manager.config_manager.global_settings_data['General']['flaresolverr'],
        vi_mode=manager.vi_mode,
    ).execute()
    max_filename_length = inquirer.number(
        message="Max Filename Length:",
        default=int(manager.config_manager.global_settings_data['General']['max_file_name_length']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    max_folder_name_length = inquirer.number(
        message="Max Folder Name Length:",
        default=int(manager.config_manager.global_settings_data['General']['max_folder_name_length']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    required_free_space = inquirer.number(
        message="Required Free Space (in GB):",
        default=int(manager.config_manager.global_settings_data['General']['required_free_space']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()

    manager.config_manager.global_settings_data['General']['allow_insecure_connections'] = allow_insecure_connections
    manager.config_manager.global_settings_data['General']['user_agent'] = user_agent
    manager.config_manager.global_settings_data['General']['proxy'] = proxy
    manager.config_manager.global_settings_data['General']['flaresolverr'] = flaresolverr
    manager.config_manager.global_settings_data['General']['max_filename_length'] = int(max_filename_length)
    manager.config_manager.global_settings_data['General']['max_folder_name_length'] = int(max_folder_name_length)
    manager.config_manager.global_settings_data['General']['required_free_space'] = int(required_free_space)


def edit_ui_settings_prompt(manager: Manager) -> None:
    """Edit the progress settings"""
    console.clear()
    console.print("Editing UI Settings")
    refresh_rate = inquirer.number(
        message="Refresh Rate:",
        default=int(manager.config_manager.global_settings_data['UI_Options']['refresh_rate']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    scraping_item_limit = inquirer.number(
        message="Number of lines to allow for scraping items before overflow:",
        default=int(manager.config_manager.global_settings_data['UI_Options']['scraping_item_limit']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    downloading_item_limit = inquirer.number(
        message="Number of lines to allow for download items before overflow:",
        default=int(manager.config_manager.global_settings_data['UI_Options']['downloading_item_limit']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    
    vi_mode = inquirer.confirm(
        message="Enable VI/VIM keybindings?",
        default=bool(manager.config_manager.global_settings_data['UI_Options']['vi_mode']),
        vi_mode=manager.vi_mode,
    ).execute()

    manager.config_manager.global_settings_data['UI_Options']['refresh_rate'] = int(refresh_rate)
    manager.config_manager.global_settings_data['UI_Options']['scraping_item_limit'] = int(scraping_item_limit)
    manager.config_manager.global_settings_data['UI_Options']['downloading_item_limit'] = int(downloading_item_limit)
    manager.config_manager.global_settings_data['UI_Options']['vi_mode'] = vi_mode
    manager.vi_mode = vi_mode


def edit_rate_limiting_settings_prompt(manager: Manager) -> None:
    """Edit the rate limiting settings"""
    console.clear()
    console.print("Editing Rate Limiting Settings")
    connection_timeout = inquirer.number(
        message="Connection Timeout (in seconds):",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['connection_timeout']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    read_timeout = inquirer.number(
        message="Read Timeout (in seconds):",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['read_timeout']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    download_attempts = inquirer.number(
        message="Download Attempts:",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_attempts']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    rate_limit = inquirer.number(
        message="Maximum number of requests per second:",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['rate_limit']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    throttle = inquirer.number(
        message="Delay between requests during the download stage:",
        default=float(manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_delay']),
        float_allowed=True,
        vi_mode=manager.vi_mode,
    ).execute()

    max_simultaneous_downloads = inquirer.number(
        message="Maximum number of simultaneous downloads:",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()
    max_simultaneous_downloads_per_domain = inquirer.number(
        message="Maximum number of simultaneous downloads per domain:",
        default=int(manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain']),
        float_allowed=False,
        vi_mode=manager.vi_mode,
    ).execute()

    manager.config_manager.global_settings_data['Rate_Limiting_Options']['connection_timeout'] = int(connection_timeout)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['read_timeout'] = int(read_timeout)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_attempts'] = int(download_attempts)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['rate_limit'] = int(rate_limit)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_delay'] = float(throttle)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'] = int(max_simultaneous_downloads)
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'] = int(max_simultaneous_downloads_per_domain)
