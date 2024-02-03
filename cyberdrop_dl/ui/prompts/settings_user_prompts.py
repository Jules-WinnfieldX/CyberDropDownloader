from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import PathValidator, EmptyInputValidator, NumberValidator
from rich.console import Console

from cyberdrop_dl.utils.dataclasses.supported_domains import SupportedDomains

if TYPE_CHECKING:
    from typing import Dict

    from cyberdrop_dl.managers.manager import Manager

console = Console()


def create_new_config_prompt(manager: Manager) -> None:
    """Create a new config file"""
    console.clear()
    console.print("Create a new config file")
    config_name = inquirer.text(
        message="Enter the name of the config:",
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    if (manager.path_manager.config_dir / config_name).is_dir():
        console.print(f"Config with name '{config_name}' already exists!")
        inquirer.confirm(message="Press enter to return to the main menu.").execute()
        return
    manager.config_manager.change_config(config_name)
    edit_config_values_prompt(manager)


def edit_config_values_prompt(manager: Manager) -> None:
    """Edit the config values"""
    config = manager.config_manager.settings_data

    while True:
        console.clear()
        console.print("Editing Config Values")
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                Choice(1, "Edit Download Options"),
                Choice(2, "Edit Input / Output File Paths"),
                Choice(3, "Edit Log File Naming / Path"),
                Choice(4, "Edit File Size Limits"),
                Choice(5, "Edit Ignore Options"),
                Choice(6, "Edit Runtime Options"),
                Choice(7, "Edit Sorting Options"),
                Choice(8, "Done"),
            ], long_instruction="ARROW KEYS: Navigate | ENTER: Select"
        ).execute()

        # Edit Download Options
        if action == 1:
            edit_download_options_prompt(config)

        # Edit Input / Output File Paths
        elif action == 2:
            edit_input_output_file_paths_prompt(config)

        # Edit Log File Naming / Path
        elif action == 3:
            edit_log_file_naming_path_prompt(config)

        # Edit File Size Limits
        elif action == 4:
            edit_file_size_limits_prompt(config)

        # Edit Ignore Options
        elif action == 5:
            edit_ignore_options_prompt(config)

        # Edit Runtime Options
        elif action == 6:
            edit_runtime_options_prompt(config)

        # Edit Sorting Options
        elif action == 7:
            edit_sort_options_prompt(config)

        # Done
        elif action == 8:
            manager.config_manager.settings_data = config
            manager.config_manager.write_updated_settings_config()
            return


def edit_download_options_prompt(config: Dict) -> None:
    """Edit the download options"""
    console.clear()
    action = inquirer.checkbox(
        message="Select the download options you want to enable:",
        choices=[
            Choice(value="block_download_sub_folders",
                   name="Block Download Sub Folders",
                   enabled=config["Download_Options"]["block_download_sub_folders"]),
            Choice(value="disable_download_attempt_limit",
                   name="Disable Download Attempt Limit",
                   enabled=config["Download_Options"]["disable_download_attempt_limit"]),
            Choice(value="disable_file_timestamps",
                   name="Disable File Timestamps Editing",
                   enabled=config["Download_Options"]["disable_file_timestamps"]),
            Choice(value="include_album_id_in_folder_name",
                   name="Include Album ID In Folder Name",
                   enabled=config["Download_Options"]["include_album_id_in_folder_name"]),
            Choice(value="include_thread_id_in_folder_name",
                   name="Include Thread ID In Folder Name",
                   enabled=config["Download_Options"]["include_album_id_in_folder_name"]),
            Choice(value="remove_domains_from_folder_names",
                   name="Remove Domains From Folder Names",
                   enabled=config["Download_Options"]["remove_domains_from_folder_names"]),
            Choice(value="remove_generated_id_from_filenames",
                   name="Remove Generated ID From Filenames",
                   enabled=config["Download_Options"]["remove_generated_id_from_filenames"]),
            Choice(value="scrape_single_forum_post",
                   name="Scrape Single Forum Post",
                   enabled=config["Download_Options"]["scrape_single_forum_post"]),
            Choice(value="separate_posts",
                   name="Separate Posts Into Folders",
                   enabled=config["Download_Options"]["separate_posts"]),
            Choice(value="skip_download_mark_completed",
                   name="Skip Download and Mark it as Completed",
                   enabled=config["Download_Options"]["skip_download_mark_completed"]),
        ], long_instruction="ARROW KEYS: Navigate | TAB: Select | ENTER: Confirm"
    ).execute()

    for key in config["Download_Options"]:
        config["Download_Options"][key] = False

    for key in action:
        config["Download_Options"][key] = True


def edit_input_output_file_paths_prompt(config: Dict) -> None:
    """Edit the input / output file paths"""
    console.clear()
    console.print("Editing Input / Output File Paths")
    input_file = inquirer.filepath(
        message="Enter the input file path:",
        default=str(config['Files']['input_file']),
        validate=PathValidator(is_file=True, message="Input is not a file")
    ).execute()
    download_folder = inquirer.text(
        message="Enter the download folder path:",
        default=str(config['Files']['download_folder']),
        validate=PathValidator(is_dir=True, message="Input is not a directory")
    ).execute()

    config['Files']['input_file'] = Path(input_file)
    config['Files']['download_folder'] = Path(download_folder)


def edit_log_file_naming_path_prompt(config: Dict) -> None:
    """Edit the log file naming / path"""
    console.clear()
    console.print("Editing Log File Naming / Path")
    log_folder = inquirer.filepath(
        message="Enter the log folder path:",
        default=str(config['Logs']['log_folder']),
        validate=PathValidator(is_dir=True, message="Input is not a directory")
    ).execute()
    main_log_filename = inquirer.text(
        message="Enter the main log file name:",
        default=config['Logs']['main_log_filename'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    last_forum_post_filename = inquirer.text(
        message="Enter the last forum post log file name:",
        default=config['Logs']['last_forum_post_filename'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    unsupported_urls_filename = inquirer.text(
        message="Enter the unsupported urls log file name:",
        default=config['Logs']['unsupported_urls_filename'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    download_error_urls_filename = inquirer.text(
        message="Enter the download error urls log file name:",
        default=config['Logs']['download_error_urls_filename'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()
    scrape_error_urls_filename = inquirer.text(
        message="Enter the scrape error urls log file name:",
        default=config['Logs']['scrape_error_urls_filename'],
        validate=EmptyInputValidator("Input should not be empty")
    ).execute()

    config['Logs']['log_folder'] = Path(log_folder)
    config['Logs']['main_log_filename'] = main_log_filename
    config['Logs']['last_forum_post_filename'] = last_forum_post_filename
    config['Logs']['unsupported_urls_filename'] = unsupported_urls_filename
    config['Logs']['download_error_urls_filename'] = download_error_urls_filename
    config['Logs']['scrape_error_urls_filename'] = scrape_error_urls_filename


def edit_file_size_limits_prompt(config: Dict) -> None:
    """Edit the file size limits"""
    console.clear()
    console.print("Editing File Size Limits")
    maximum_image_size = inquirer.number(
        message="Enter the maximum image size:",
        default=int(config['File_Size_Limits']['maximum_image_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()
    maximum_video_size = inquirer.number(
        message="Enter the maximum video size:",
        default=int(config['File_Size_Limits']['maximum_video_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()
    maximum_other_size = inquirer.number(
        message="Enter the maximum other file type size:",
        default=int(config['File_Size_Limits']['maximum_other_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()
    minimum_image_size = inquirer.number(
        message="Enter the minimum image size:",
        default=int(config['File_Size_Limits']['minimum_image_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()
    minimum_video_size = inquirer.number(
        message="Enter the minimum video size:",
        default=int(config['File_Size_Limits']['minimum_video_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()
    minimum_other_size = inquirer.number(
        message="Enter the minimum other file type size:",
        default=int(config['File_Size_Limits']['minimum_other_size']),
        validate=NumberValidator(),
        long_instruction="This value is in bytes (0 is no limit)",
    ).execute()

    config['File_Size_Limits']['maximum_image_size'] = int(maximum_image_size)
    config['File_Size_Limits']['maximum_video_size'] = int(maximum_video_size)
    config['File_Size_Limits']['maximum_other_size'] = int(maximum_other_size)
    config['File_Size_Limits']['minimum_image_size'] = int(minimum_image_size)
    config['File_Size_Limits']['minimum_video_size'] = int(minimum_video_size)
    config['File_Size_Limits']['minimum_other_size'] = int(minimum_other_size)


def edit_ignore_options_prompt(config: Dict) -> None:
    """Edit the ignore options"""
    console.clear()
    console.print("Editing Ignore Options")
    action = inquirer.checkbox(
        message="Select the ignore options you want to enable:",
        choices=[
            Choice(value="exclude_videos",
                   name="Don't download videos files",
                   enabled=config["Ignore_Options"]["exclude_videos"]),
            Choice(value="exclude_images",
                   name="Don't download images files",
                   enabled=config["Ignore_Options"]["exclude_images"]),
            Choice(value="exclude_audio",
                   name="Don't download audio files",
                   enabled=config["Ignore_Options"]["exclude_audio"]),
            Choice(value="exclude_other",
                   name="Don't download other files",
                   enabled=config["Ignore_Options"]["exclude_other"]),
            Choice(value="ignore_coomer_ads",
                   name="Ignore coomer ads when scraping",
                   enabled=config["Ignore_Options"]["ignore_coomer_ads"]),
        ], long_instruction="ARROW KEYS: Move | TAB: Select | ENTER: Confirm",
    ).execute()

    for key in config["Ignore_Options"]:
        config["Ignore_Options"][key] = False

    for key in action:
        config["Ignore_Options"][key] = True

    skip_choices = list(SupportedDomains.supported_hosts)
    skip_choices.insert(0, "None")
    skip_hosts = inquirer.fuzzy(
        choices=skip_choices,
        multiselect=True,
        message="Select any sites you want to ignore while scraping:",
        long_instruction="ARROW KEYS: Move | TYPE: Filter | TAB: Select | ENTER: Confirm",
    ).execute()

    skip_hosts = [host for host in skip_hosts if host in SupportedDomains.supported_hosts]
    config["Ignore_Options"]["skip_hosts"] = skip_hosts

    only_choices = list(SupportedDomains.supported_hosts)
    only_choices.insert(0, "None")
    only_hosts = inquirer.fuzzy(
        choices=only_choices,
        multiselect=True,
        message="Select only the sites you want to scrape from:",
        long_instruction="ARROW KEYS: Move | TYPE: Filter | TAB: Select | ENTER: Confirm",
    ).execute()

    only_hosts = [host for host in only_hosts if host in SupportedDomains.supported_hosts]
    config["Ignore_Options"]["only_hosts"] = only_hosts


def edit_runtime_options_prompt(config: Dict) -> None:
    """Edit the runtime options"""
    console.clear()
    console.print("Editing Runtime Options")
    action = inquirer.checkbox(
        message="Select the runtime options you want to enable:",
        choices=[
            Choice(value="ignore_history",
                   name="Ignore the history (previously downloaded files)",
                   enabled=config["Runtime_Options"]["ignore_history"]),
            Choice(value="skip_check_for_partial_files",
                   name="Skip checking for partial files in the download folder",
                   enabled=config["Runtime_Options"]["skip_check_for_partial_files"]),
            Choice(value="skip_check_for_empty_folders",
                   name="Skip checking for empty folders in the download folder",
                   enabled=config["Runtime_Options"]["skip_check_for_empty_folders"]),
            Choice(value="delete_partial_files",
                   name="Delete partial files in the download folder",
                   enabled=config["Runtime_Options"]["delete_partial_files"]),
            Choice(value="send_unsupported_to_jdownloader",
                   name="Send unsupported urls to JDownloader to download",
                   enabled=config["Runtime_Options"]["send_unsupported_to_jdownloader"]),
        ], long_instruction="ARROW KEYS: Move | TAB: Select | ENTER: Confirm",
    ).execute()

    log_level = inquirer.number(
        message="Enter the log level:",
        default=int(config['Runtime_Options']['log_level']),
        validate=NumberValidator(),
        long_instruction="10 is the default (uses pythons logging numerical levels)",
    ).execute()

    for key in config["Runtime_Options"]:
        config["Runtime_Options"][key] = False

    for key in action:
        config["Runtime_Options"][key] = True

    config['Runtime_Options']['log_level'] = int(log_level)


def edit_sort_options_prompt(config: Dict) -> None:
    """Edit the sort options"""
    console.clear()
    console.print("Editing Sort Options")
    config["Sorting"]["sort_downloads"] = False
    sort_downloads = inquirer.confirm(message="Do you want Cyberdrop-DL to sort files for you?").execute()
    if sort_downloads:
        config["Sorting"]["sort_downloads"] = True
        sort_folder = inquirer.filepath(
            message="Enter the folder you want to sort files into:",
            default=str(config['Sorting']['sort_folder']),
            validate=PathValidator(is_dir=True, message="Input is not a directory"),
        ).execute()
        sort_incremementer_format = inquirer.text(
            message="Enter the sort incrementer format:",
            default=config['Sorting']['sort_incremementer_format'],
            validate=EmptyInputValidator("Input should not be empty")
        ).execute()
        sorted_audio = inquirer.text(
            message="Enter the format you want to sort audio files into:",
            default=config['Sorting']['sorted_audio'],
            validate=EmptyInputValidator("Input should not be empty")
        ).execute()
        sorted_video = inquirer.text(
            message="Enter the format you want to sort video files into:",
            default=config['Sorting']['sorted_video'],
            validate=EmptyInputValidator("Input should not be empty")
        ).execute()
        sorted_image = inquirer.text(
            message="Enter the format you want to sort image files into:",
            default=config['Sorting']['sorted_image'],
            validate=EmptyInputValidator("Input should not be empty")
        ).execute()
        sorted_other = inquirer.text(
            message="Enter the format you want to sort other files into:",
            default=config['Sorting']['sorted_other'],
            validate=EmptyInputValidator("Input should not be empty")
        ).execute()

        config['Sorting']['sort_folder'] = Path(sort_folder)
        config['Sorting']['sort_incremementer_format'] = sort_incremementer_format
        config['Sorting']['sorted_audio'] = sorted_audio
        config['Sorting']['sorted_video'] = sorted_video
        config['Sorting']['sorted_image'] = sorted_image
        config['Sorting']['sorted_other'] = sorted_other
