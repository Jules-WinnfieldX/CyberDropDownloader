import copy
import shutil
from dataclasses import field
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

import yaml

from cyberdrop_dl.utils.args.config_definitions import authentication_settings, settings, global_settings

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


def _match_config_dicts(default: Dict, existing: Dict) -> Dict:
    """Matches the keys of two dicts and returns the default dict with the values of the existing dict"""
    for group in default:
        for key in default[group]:
            if group in existing:
                if key in existing[group]:
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

        self.authentication_settings: Path = field(init=False)
        self.settings: Path = field(init=False)
        self.global_settings: Path = field(init=False)

        self.loaded_config: str = field(init=False)

        self.authentication_data: Dict = field(init=False)
        self.settings_data: Dict = field(init=False)
        self.global_settings_data: Dict = field(init=False)

    def startup(self) -> None:
        """Startup process for the config manager"""
        self.authentication_settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.global_settings.parent.mkdir(parents=True, exist_ok=True)

        if not self.authentication_settings.exists():
            _save_yaml(self.authentication_settings, authentication_settings)
            self.authentication_data = copy.deepcopy(authentication_settings)
        else:
            self._verify_authentication_config()

        if not self.settings.exists():
            _save_yaml(self.settings, settings)
            self.settings_data = copy.deepcopy(settings)
        else:
            self._verify_settings_config()

        if not self.global_settings.exists():
            _save_yaml(self.global_settings, global_settings)
            self.global_settings_data = copy.deepcopy(global_settings)
        else:
            self._verify_global_settings_config()

    def _verify_authentication_config(self) -> None:
        """Verifies the authentication config file and creates it if it doesn't exist"""
        default_auth_data = copy.deepcopy(authentication_settings)
        existing_auth_data = _load_yaml(self.authentication_settings)
        self.authentication_data = _match_config_dicts(default_auth_data, existing_auth_data)
        _save_yaml(self.authentication_settings, self.authentication_data)

    def _verify_settings_config(self) -> None:
        """Verifies the settings config file and creates it if it doesn't exist"""
        default_settings_data = settings
        existing_settings_data = _load_yaml(self.settings)
        self.settings_data = _match_config_dicts(default_settings_data, existing_settings_data)
        _save_yaml(self.settings, self.settings_data)

    def _verify_global_settings_config(self) -> None:
        """Verifies the global settings config file and creates it if it doesn't exist"""
        default_global_settings_data = global_settings
        existing_global_settings_data = _load_yaml(self.global_settings)
        self.global_settings_data = _match_config_dicts(default_global_settings_data, existing_global_settings_data)
        _save_yaml(self.global_settings, self.global_settings_data)

    def set_new_settings_config(self, config_path: Path) -> None:
        """Sets a new settings config file"""
        self.settings = config_path
        self._verify_settings_config()

    def create_new_config(self, config_name: str, settings_data: Dict) -> None:
        """Creates a new settings config file"""
        new_settings = self.manager.directory_manager.configs / config_name / "settings.yaml"
        new_logs = self.manager.directory_manager.configs / config_name / "Logs"
        new_urls = self.manager.directory_manager.configs / config_name / "URLs.txt"
        new_settings.parent.mkdir(parents=True, exist_ok=True)
        new_logs.mkdir(parents=True, exist_ok=True)
        new_urls.touch(exist_ok=True)
        _save_yaml(new_settings, settings_data)

    def write_updated_authentication_config(self) -> None:
        """Write updated authentication data"""
        _save_yaml(self.authentication_settings, self.authentication_data)

    def write_updated_settings_config(self) -> None:
        """Write updated settings data"""
        _save_yaml(self.settings, self.settings_data)

    def write_updated_global_settings_config(self) -> None:
        """Write updated global settings data"""
        _save_yaml(self.global_settings, self.global_settings_data)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    def get_configs(self) -> List:
        """Returns a list of all the configs"""
        return [config.name for config in self.manager.directory_manager.configs.iterdir() if config.is_dir()]

    def load_config(self, config_name: str) -> None:
        """Loads a config"""
        self.loaded_config = config_name
        self.manager.startup()

    def change_default_config(self, config_name: str) -> None:
        """Changes the default config"""
        self.manager.cache_manager.save("default_config", config_name)

    def new_config(self, config_name: str) -> None:
        """Creates a new config"""
        (self.manager.directory_manager.configs / config_name).mkdir(exist_ok=True, parents=True)
        self.loaded_config = config_name
        self.settings = self.manager.directory_manager.configs / config_name / "settings.yaml"
        self.write_updated_settings_config()
        self.manager.startup()

    def delete_config(self, config_name: str) -> None:
        """Deletes a config"""
        configs = self.get_configs()
        configs.remove(config_name)
        self.startup()

        config = self.manager.directory_manager.configs / config_name
        shutil.rmtree(config)
