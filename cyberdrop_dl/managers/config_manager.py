import asyncio
import copy
import shutil
from dataclasses import field
from pathlib import Path
from time import sleep
from typing import Dict, List, TYPE_CHECKING

import yaml

from cyberdrop_dl.managers.log_manager import LogManager
from cyberdrop_dl.utils.args.config_definitions import authentication_settings, settings, global_settings

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


def _match_config_dicts(default: Dict, existing: Dict) -> Dict:
    """Matches the keys of two dicts and returns the default dict with the values of the existing dict"""
    for group in default:
        for key in default[group]:
            if group in existing and key in existing[group]:
                default[group][key] = existing[group][key]
    return default


def _save_yaml(file: Path, data: Dict) -> None:
    """Saves a dict to a yaml file"""
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, 'w') as yaml_file:
        yaml.dump(data, yaml_file)


def _load_yaml(file: Path) -> Dict:
    """Loads a yaml file and returns it as a dict"""
    with open(file, 'r') as yaml_file:
        return yaml.load(yaml_file.read(), Loader=yaml.FullLoader)


class ConfigManager:
    def __init__(self, manager: 'Manager'):
        self.manager = manager
        self.loaded_config: str = field(init=False)

        self.authentication_settings: Path = field(init=False)
        self.settings: Path = field(init=False)
        self.global_settings: Path = field(init=False)

        self.authentication_data: Dict = field(init=False)
        self.settings_data: Dict = field(init=False)
        self.global_settings_data: Dict = field(init=False)

    def startup(self) -> None:
        """Pre-startup process for the config manager"""
        if not isinstance(self.loaded_config, str):
            self.loaded_config = self.manager.cache_manager.get("default_config")
            if not self.loaded_config:
                self.loaded_config = "Default"
            if self.manager.args_manager.load_config_from_args:
                self.loaded_config = self.manager.args_manager.load_config_name

        self.authentication_settings = self.manager.path_manager.config_dir / "authentication.yaml"
        self.global_settings = self.manager.path_manager.config_dir / "global_settings.yaml"
        self.settings = self.manager.path_manager.config_dir / self.loaded_config / "settings.yaml"

        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.load_configs()

    def load_configs(self) -> None:
        """Loads all the configs"""
        if self.authentication_settings.is_file():
            self._verify_authentication_config()
        else:
            self.authentication_data = copy.deepcopy(authentication_settings)
            _save_yaml(self.authentication_settings, self.authentication_data)

        if self.global_settings.is_file():
            self._verify_global_settings_config()
        else:
            self.global_settings_data = copy.deepcopy(global_settings)
            _save_yaml(self.global_settings, self.global_settings_data)

        if self.manager.args_manager.config_file:
            self.settings = Path(self.manager.args_manager.config_file)
            self.loaded_config = "CLI-Arg Specified"

        if self.settings.is_file():
            self._verify_settings_config()
        else:
            from cyberdrop_dl.managers.path_manager import APP_STORAGE, DOWNLOAD_STORAGE
            self.settings_data = copy.deepcopy(settings)
            self.settings_data['Files']['input_file'] = APP_STORAGE / "Configs" / self.loaded_config / "URLs.txt"
            self.settings_data['Files']['download_folder'] = DOWNLOAD_STORAGE / "Cyberdrop-DL Downloads"
            self.settings_data["Logs"]["log_folder"] = APP_STORAGE / "Configs" / self.loaded_config / "Logs"
            self.settings_data['Sorting']['sort_folder'] = DOWNLOAD_STORAGE / "Cyberdrop-DL Sorted Downloads"
            self.write_updated_settings_config()

    def _verify_authentication_config(self) -> None:
        """Verifies the authentication config file and creates it if it doesn't exist"""
        default_auth_data = copy.deepcopy(authentication_settings)
        existing_auth_data = _load_yaml(self.authentication_settings)
        self.authentication_data = _match_config_dicts(default_auth_data, existing_auth_data)
        _save_yaml(self.authentication_settings, self.authentication_data)

    def _verify_settings_config(self) -> None:
        """Verifies the settings config file and creates it if it doesn't exist"""
        default_settings_data = copy.deepcopy(settings)
        existing_settings_data = _load_yaml(self.settings)
        self.settings_data = _match_config_dicts(default_settings_data, existing_settings_data)
        self.settings_data['Files']['input_file'] = Path(self.settings_data['Files']['input_file'])
        self.settings_data['Files']['download_folder'] = Path(self.settings_data['Files']['download_folder'])
        self.settings_data["Logs"]["log_folder"] = Path(self.settings_data["Logs"]["log_folder"])
        self.settings_data['Sorting']['sort_folder'] = Path(self.settings_data['Sorting']['sort_folder'])

        # change to ints
        self.settings_data['File_Size_Limits']['maximum_image_size'] = int(self.settings_data['File_Size_Limits']['maximum_image_size'])
        self.settings_data['File_Size_Limits']['maximum_video_size'] = int(self.settings_data['File_Size_Limits']['maximum_video_size'])
        self.settings_data['File_Size_Limits']['maximum_other_size'] = int(self.settings_data['File_Size_Limits']['maximum_other_size'])
        self.settings_data['File_Size_Limits']['minimum_image_size'] = int(self.settings_data['File_Size_Limits']['minimum_image_size'])
        self.settings_data['File_Size_Limits']['minimum_video_size'] = int(self.settings_data['File_Size_Limits']['minimum_video_size'])
        self.settings_data['File_Size_Limits']['minimum_other_size'] = int(self.settings_data['File_Size_Limits']['minimum_other_size'])

        self.global_settings_data['General']['max_file_name_length'] = int(self.global_settings_data['General']['max_file_name_length'])
        self.global_settings_data['General']['max_folder_name_length'] = int(self.global_settings_data['General']['max_folder_name_length'])
        self.global_settings_data['Rate_Limiting_Options']['connection_timeout'] = int(self.global_settings_data['Rate_Limiting_Options']['connection_timeout'])
        self.global_settings_data['Rate_Limiting_Options']['download_attempts'] = int(self.global_settings_data['Rate_Limiting_Options']['download_attempts'])
        self.global_settings_data['Rate_Limiting_Options']['download_delay'] = int(self.global_settings_data['Rate_Limiting_Options']['download_delay'])
        self.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'] = int(self.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads'])
        self.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'] = int(self.global_settings_data['Rate_Limiting_Options']['max_simultaneous_downloads_per_domain'])
        self.global_settings_data['Rate_Limiting_Options']['rate_limit'] = int(self.global_settings_data['Rate_Limiting_Options']['rate_limit'])
        self.global_settings_data['Rate_Limiting_Options']['read_timeout'] = int(self.global_settings_data['Rate_Limiting_Options']['read_timeout'])

        save_data = copy.deepcopy(self.settings_data)
        save_data['Files']['input_file'] = str(save_data['Files']['input_file'])
        save_data['Files']['download_folder'] = str(save_data['Files']['download_folder'])
        save_data["Logs"]["log_folder"] = str(save_data["Logs"]["log_folder"])
        save_data['Sorting']['sort_folder'] = str(save_data['Sorting']['sort_folder'])
        _save_yaml(self.settings, save_data)

    def _verify_global_settings_config(self) -> None:
        """Verifies the global settings config file and creates it if it doesn't exist"""
        default_global_settings_data = copy.deepcopy(global_settings)
        existing_global_settings_data = _load_yaml(self.global_settings)
        self.global_settings_data = _match_config_dicts(default_global_settings_data, existing_global_settings_data)
        _save_yaml(self.global_settings, self.global_settings_data)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    def create_new_config(self, new_settings: Path, settings_data: Dict) -> None:
        """Creates a new settings config file"""
        settings_data['Files']['input_file'] = str(settings_data['Files']['input_file'])
        settings_data['Files']['download_folder'] = str(settings_data['Files']['download_folder'])
        settings_data["Logs"]["log_folder"] = str(settings_data["Logs"]["log_folder"])
        settings_data['Sorting']['sort_folder'] = str(settings_data['Sorting']['sort_folder'])
        _save_yaml(new_settings, settings_data)

    def write_updated_authentication_config(self) -> None:
        """Write updated authentication data"""
        _save_yaml(self.authentication_settings, self.authentication_data)

    def write_updated_settings_config(self) -> None:
        """Write updated settings data"""
        settings_data = copy.deepcopy(self.settings_data)
        settings_data['Files']['input_file'] = str(settings_data['Files']['input_file'])
        settings_data['Files']['download_folder'] = str(settings_data['Files']['download_folder'])
        settings_data["Logs"]["log_folder"] = str(settings_data["Logs"]["log_folder"])
        settings_data['Sorting']['sort_folder'] = str(settings_data['Sorting']['sort_folder'])
        _save_yaml(self.settings, settings_data)

    def write_updated_global_settings_config(self) -> None:
        """Write updated global settings data"""
        _save_yaml(self.global_settings, self.global_settings_data)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    def get_configs(self) -> List:
        """Returns a list of all the configs"""
        return [config.name for config in self.manager.path_manager.config_dir.iterdir() if config.is_dir()]

    def change_default_config(self, config_name: str) -> None:
        """Changes the default config"""
        self.manager.cache_manager.save("default_config", config_name)

    def delete_config(self, config_name: str) -> None:
        """Deletes a config"""
        configs = self.get_configs()
        configs.remove(config_name)

        if self.manager.cache_manager.get("default_config") == config_name:
            self.manager.cache_manager.save("default_config", configs[0])

        config = self.manager.path_manager.config_dir / config_name
        shutil.rmtree(config)

    def change_config(self, config_name: str) -> None:
        """Changes the config"""
        self.loaded_config = config_name
        self.startup()

        self.manager.path_manager.startup()
        sleep(1)
        self.manager.log_manager = LogManager(self.manager)
        sleep(1)
