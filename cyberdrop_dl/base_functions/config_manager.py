from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, Optional, Union

import yaml

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.config_schema import config_default


def _to_config_value(value) -> Union[str, int]:
    return str(value) if isinstance(value, Path) else value


def _create_config(config: Path, passed_args: Optional[dict] = None, enabled=False) -> Dict:
    """Creates the default config file, or remakes it with passed arguments"""
    config_data: Dict = config_default
    if passed_args:
        config_data["Apply_Config"] = enabled
        for group in config_data["Configuration"].values():
            for arg in group:
                if arg in passed_args:
                    group[arg] = _to_config_value(passed_args[arg])

    with open(config, 'w') as yamlfile:
        yaml.dump(config_data, yamlfile)

    return config_data


def _validate_config(config: Path) -> Dict:
    """Validates the existing config file"""
    with open(config, "r") as yamlfile:
        config_data = yaml.load(yamlfile, Loader=yaml.FullLoader)
    try:
        data = config_data["Configuration"]
        enabled = config_data["Apply_Config"]

        config_groups: Dict = config_default["Configuration"]
        if all(set(group) <= set(data[group_name]) for group_name, group in config_groups.items()):
            return config_data

        config.unlink()

        args = {}
        for group_name in config_groups:
            args.update(data[group_name])
        config_data = _create_config(config, args, enabled)

    except (KeyError, TypeError):
        config.unlink()
        config_data = _create_config(config)

    return config_data


def run_args(config: Path, cmd_arg: Dict) -> Dict:
    """Returns the proper runtime arguments based on the config and command line arguments"""
    data = _validate_config(config) if config.is_file() else _create_config(config, cmd_arg)
    if data['Apply_Config']:
        log("Running using config arguments")
        data = data["Configuration"]
        for file, path in data['Files'].items():
            data['Files'][file] = Path(path)
        data['Sorting']['sort_directory'] = Path(data['Sorting']['sort_directory'])
        return data
    else:
        log("Running using command line arguments. If you are trying to use the config file, change 'Apply_Config' to True")

    config_data: Dict = config_default["Configuration"]
    for group in config_data.values():
        for arg in group:
            if arg in cmd_arg:
                group[arg] = cmd_arg[arg]
    return config_data


async def document_args(args: Dict) -> None:
    """We document the runtime arguments for debugging and troubleshooting, redacting sensitive information"""
    print_args = copy.deepcopy(args)

    log("Starting Cyberdrop-DL")
    for group_name, group in print_args.items():
        args_type = group_name.replace('_', ' ').lower()
        for arg in group:
            if group[arg] is not None and any(s in arg for s in ('api_key', 'password', 'imgur', 'reddit')):
                group[arg] = '!REDACTED!'
        log(f"Using {args_type} arguments: {group}", quiet=True)
