from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from rich.console import Console

from cyberdrop_dl import __version__
from cyberdrop_dl.ui.prompts.settings_authentication_prompts import edit_authentication_values_prompt
from cyberdrop_dl.ui.prompts.general_prompts import (
    main_prompt, select_config_prompt, donations_prompt,
    import_cyberdrop_v4_items_prompt, manage_configs_prompt)
from cyberdrop_dl.ui.prompts.settings_global_prompts import edit_global_settings_prompt
from cyberdrop_dl.ui.prompts.url_file_prompts import edit_urls_prompt
from cyberdrop_dl.ui.prompts.settings_user_prompts import create_new_config_prompt, edit_config_values_prompt

console = Console()

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


def program_ui(manager: Manager):
    """Program UI"""
    while True:
        console.clear()
        console.print(f"[bold]Cyberdrop Downloader (V{str(__version__)})[/bold]")
        console.print(f"[bold]Current Config:[/bold] {manager.config_manager.loaded_config}")

        action = main_prompt(manager)

        # Download
        if action == 1:
            break

        # Download (All Configs)
        if action == 2:
            manager.args_manager.all_configs = True
            break

        # Retry Failed Downloads
        elif action == 3:
            manager.args_manager.retry = True
            break

        # Edit URLs
        elif action == 4:
            input_file = manager.config_manager.settings_data['Files']['input_file'] if not manager.args_manager.input_file else manager.args_manager.input_file
            edit_urls_prompt(input_file)

        # Select Config
        elif action == 5:
            configs = manager.config_manager.get_configs()
            selected_config = select_config_prompt(configs)
            manager.config_manager.change_config(selected_config)

        elif action == 6:
            console.clear()
            console.print("Editing Input / Output File Paths")
            input_file = inquirer.filepath(
                message="Enter the input file path:",
                default=str(manager.config_manager.settings_data['Files']['input_file']),
                validate=PathValidator(is_file=True, message="Input is not a file")
            ).execute()
            download_folder = inquirer.text(
                message="Enter the download folder path:",
                default=str(manager.config_manager.settings_data['Files']['download_folder']),
                validate=PathValidator(is_dir=True, message="Input is not a directory")
            ).execute()

            manager.config_manager.settings_data['Files']['input_file'] = Path(input_file)
            manager.config_manager.settings_data['Files']['download_folder'] = Path(download_folder)
            manager.config_manager.write_updated_settings_config()

        # Manage Configs
        elif action == 7:
            while True:
                console.clear()
                console.print("[bold]Manage Configs[/bold]")
                console.print(f"[bold]Current Config:[/bold] {manager.config_manager.loaded_config}")

                action = manage_configs_prompt()

                # Change Default Config
                if action == 1:
                    configs = manager.config_manager.get_configs()
                    selected_config = select_config_prompt(configs)
                    manager.config_manager.change_default_config(selected_config)

                # Create A Config
                elif action == 2:
                    create_new_config_prompt(manager)

                # Delete A Config
                elif action == 3:
                    configs = manager.config_manager.get_configs()
                    if len(configs) != 1:
                        selected_config = select_config_prompt(configs)
                        if selected_config == manager.config_manager.loaded_config:
                            inquirer.confirm(
                                message="You cannot delete the currently active config, press enter to continue.",
                                default=False,
                            ).execute()
                            continue
                        manager.config_manager.delete_config(selected_config)
                    else:
                        inquirer.confirm(
                            message="There is only one config, press enter to continue.",
                            default=False,
                        ).execute()

                # Edit Config
                elif action == 4:
                    edit_config_values_prompt(manager)

                # Edit Authentication Values
                elif action == 5:
                    edit_authentication_values_prompt(manager)

                # Edit Global Settings
                elif action == 6:
                    edit_global_settings_prompt(manager)

                # Done
                elif action == 7:
                    break

        # Import Cyberdrop_V4 Items
        elif action == 8:
            import_cyberdrop_v4_items_prompt(manager)

        # Donate
        elif action == 9:
            donations_prompt()

        # Exit
        elif action == 10:
            exit(0)
