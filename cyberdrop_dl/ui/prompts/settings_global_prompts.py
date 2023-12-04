from __future__ import annotations

from typing import TYPE_CHECKING

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator, NumberValidator
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
                Choice(3, "Done"),
            ],
        ).execute()

        # Edit General Settings
        if action == 1:
            edit_general_settings_prompt(manager)

        # Edit Rate Limiting Settings
        elif action == 2:
            edit_rate_limiting_settings_prompt(manager)

        # Done
        elif action == 3:
            manager.config_manager.write_updated_global_settings_config()
            break


def edit_general_settings_prompt(manager: Manager) -> None:
    """Edit the general settings"""
    console.clear()
    console.print("Editing General Settings")
    allow_insecure_connections = inquirer.confirm("Allow insecure connections?").execute()
    user_agent = inquirer.text(
        message="User Agent:",
        default=manager.config_manager.global_settings_data['General']['user_agent'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    proxy = inquirer.text(
        message="Proxy:",
        default=manager.config_manager.global_settings_data['General']['proxy']
    ).execute()
    max_filename_length = inquirer.number(
        message="Max Filename Length:",
        default=manager.config_manager.global_settings_data['General']['max_file_name_length'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()
    max_folder_name_length = inquirer.number(
        message="Max Folder Name Length:",
        default=manager.config_manager.global_settings_data['General']['max_folder_name_length'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()
    required_free_space = inquirer.number(
        message="Required Free Space (in GB):",
        default=manager.config_manager.global_settings_data['General']['required_free_space'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()

    manager.config_manager.global_settings_data['General']['allow_insecure_connections'] = allow_insecure_connections
    manager.config_manager.global_settings_data['General']['user_agent'] = user_agent
    manager.config_manager.global_settings_data['General']['proxy'] = proxy
    manager.config_manager.global_settings_data['General']['max_filename_length'] = max_filename_length
    manager.config_manager.global_settings_data['General']['max_folder_name_length'] = max_folder_name_length
    manager.config_manager.global_settings_data['General']['required_free_space'] = required_free_space


def edit_progress_settings_prompt(manager: Manager) -> None:
    """Edit the progress settings"""
    console.clear()
    console.print("Editing Progress Settings")
    refresh_rate = inquirer.number(
        message="Refresh Rate:",
        default=manager.config_manager.global_settings_data['Progress_Options']['refresh_rate'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()

    manager.config_manager.global_settings_data['Progress_Options']['refresh_rate'] = refresh_rate


def edit_rate_limiting_settings_prompt(manager: Manager) -> None:
    """Edit the rate limiting settings"""
    console.clear()
    console.print("Editing Rate Limiting Settings")
    connection_timeout = inquirer.number(
        message="Connection Timeout (in seconds):",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['connection_timeout'],
        float_allowed=True,
        validate=NumberValidator("Input should be a number")
    ).execute()
    read_timeout = inquirer.number(
        message="Read Timeout (in seconds):",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['read_timeout'],
        float_allowed=True,
        validate=NumberValidator("Input should be a number")
    ).execute()
    download_attempts = inquirer.number(
        message="Download Attempts:",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_attempts'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()
    rate_limit = inquirer.number(
        message="Maximum number of requests per second:",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['rate_limit'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()
    throttle = inquirer.number(
        message="Delay between requests during the download stage:",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_delay'],
        float_allowed=False,
        validate=NumberValidator("Input should be a number")
    ).execute()

    max_simultaneous_downloads = inquirer.text(
        message="Maximum number of simultaneous downloads:",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'],
        validate=NumberValidator("Input should be a number")
    ).execute()
    max_simultaneous_downloads_per_domain = inquirer.text(
        message="Maximum number of simultaneous downloads per domain:",
        default=manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'],
        validate=NumberValidator("Input should be a number")
    ).execute()

    manager.config_manager.global_settings_data['Rate_Limiting_Options']['connection_timeout'] = connection_timeout
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['read_timeout'] = read_timeout
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_attempts'] = download_attempts
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['rate_limit'] = rate_limit
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['download_delay'] = throttle
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'] = max_simultaneous_downloads
    manager.config_manager.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'] = max_simultaneous_downloads_per_domain
