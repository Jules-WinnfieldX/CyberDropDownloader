from dataclasses import field
from pathlib import Path
from typing import Any, Dict

import yaml


def _save_yaml(file: Path, data: Dict) -> None:
    """Saves a dict to a yaml file"""
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, 'w') as yaml_file:
        yaml.dump(data, yaml_file)


def _load_yaml(file: Path) -> Dict:
    """Loads a yaml file and returns it as a dict"""
    with open(file, 'r') as yaml_file:
        return yaml.load(yaml_file.read(), Loader=yaml.FullLoader)


class CacheManager:
    def __init__(self):
        self.cache_file: Path = field(init=False)
        self.cache = {}

    def startup(self, cache_file: Path) -> None:
        """Ensures that the cache file exists"""
        self.cache_file = cache_file
        if not self.cache_file.is_file():
            self.cache['default_config'] = "Default"
            _save_yaml(self.cache_file, self.cache)
        else:
            self.load()

    def load(self):
        """Loads the cache file into memory"""
        self.cache = _load_yaml(self.cache_file)

    def get(self, key: str) -> Any:
        """Returns the value of a key in the cache"""
        return self.cache.get(key, None)

    def save(self, key: str, value: Any):
        """Saves a key and value to the cache"""
        self.cache[key] = value
        _save_yaml(self.cache_file, self.cache)

    def remove(self, key: str):
        """Removes a key from the cache"""
        if key in self.cache:
            del self.cache[key]
            _save_yaml(self.cache_file, self.cache)
