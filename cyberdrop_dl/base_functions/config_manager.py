from __future__ import annotations

import copy
from pathlib import Path

import yaml

from cyberdrop_dl.base_functions.base_functions import log
from cyberdrop_dl.base_functions.config_schema import (
    authentication_args,
    config_default,
    files_args,
    forum_args,
    ignore_args,
    jdownloader_args,
    progress_args,
    ratelimiting_args,
    runtime_args,
    sorting_args,
)


def _create_config(config: Path, passed_args: dict = None, enabled=False) -> dict:
    """Creates the default config file, or remakes it with passed arguments"""
    config_data = config_default
    if passed_args:
        config_data["Apply_Config"] = enabled
        for arg in authentication_args:
            if arg in passed_args:
                config_data["Configuration"]["Authentication"][arg] = passed_args[arg]
        for arg in files_args:
            if arg in passed_args:
                config_data["Configuration"]["Files"][arg] = str(passed_args[arg])
        for arg in ignore_args:
            if arg in passed_args:
                config_data["Configuration"]["Ignore"][arg] = passed_args[arg]
        for arg in forum_args:
            if arg in passed_args:
                config_data["Configuration"]["Forum_Options"][arg] = passed_args[arg]
        for arg in jdownloader_args:
            if arg in passed_args:
                config_data["Configuration"]["JDownloader"][arg] = passed_args[arg]
        for arg in progress_args:
            if arg in passed_args:
                config_data["Configuration"]["Progress_Options"][arg] = passed_args[arg]
        for arg in ratelimiting_args:
            if arg in passed_args:
                config_data["Configuration"]["Ratelimiting"][arg] = passed_args[arg]
        for arg in runtime_args:
            if arg in passed_args:
                config_data["Configuration"]["Runtime"][arg] = passed_args[arg]
        for arg in sorting_args:
            if arg in passed_args:
                if arg == "sort_directory":
                    config_data["Configuration"]["Sorting"][arg] = str(passed_args[arg])
                else:
                    config_data["Configuration"]["Sorting"][arg] = passed_args[arg]

    with open(config, 'w') as yamlfile:
        yaml.dump(config_data, yamlfile)

    return config_data


def _validate_config(config: Path) -> dict:
    """Validates the existing config file"""
    with open(config, "r") as yamlfile:
        config_data = yaml.load(yamlfile, Loader=yaml.FullLoader)
    try:
        data = config_data["Configuration"]
        enabled = config_data["Apply_Config"]

        if all((set(authentication_args).issubset(set(data['Authentication'])),
                set(files_args).issubset(set(data['Files'])),
                set(forum_args).issubset(set(data['Forum_Options'])),
                set(ignore_args).issubset(set(data['Ignore'])),
                set(jdownloader_args).issubset(set(data['JDownloader'])),
                set(progress_args).issubset(set(data['Progress_Options'])),
                set(ratelimiting_args).issubset(set(data['Ratelimiting'])),
                set(runtime_args).issubset(set(data['Runtime'])),
                set(sorting_args).issubset(set(data['Sorting'])))):
            return config_data

        config.unlink()

        args = {}
        args_list = [data['Authentication'], data['Files'], data['Forum_Options'], data['Ignore'],
                     data['JDownloader'], data['Progress_Options'], data['Ratelimiting'], data['Runtime'],
                     data['Sorting']]
        for dic in args_list:
            args.update(dic)
        config_data = _create_config(config, args, enabled)

    except (KeyError, TypeError):
        config.unlink()
        config_data = _create_config(config)

    return config_data


def run_args(config: Path, cmd_arg: dict) -> dict:
    """Returns the proper runtime arguments based on the config and command line arguments"""
    data = _validate_config(config) if config.is_file() else _create_config(config, cmd_arg)
    if data['Apply_Config']:
        data = data["Configuration"]
        for file, path in data['Files'].items():
            data['Files'][file] = Path(path)
        data['Sorting']['sort_directory'] = Path(data['Sorting']['sort_directory'])
        return data

    config_data = config_default["Configuration"]
    for arg in authentication_args:
        if arg in cmd_arg:
            config_data["Authentication"][arg] = cmd_arg[arg]
    for arg in files_args:
        if arg in cmd_arg:
            config_data["Files"][arg] = cmd_arg[arg]
    for arg in forum_args:
        if arg in cmd_arg:
            config_data["Forum_Options"][arg] = cmd_arg[arg]
    for arg in ignore_args:
        if arg in cmd_arg:
            config_data["Ignore"][arg] = cmd_arg[arg]
    for arg in jdownloader_args:
        if arg in cmd_arg:
            config_data["JDownloader"][arg] = cmd_arg[arg]
    for arg in progress_args:
        if arg in cmd_arg:
            config_data["Progress_Options"][arg] = cmd_arg[arg]
    for arg in ratelimiting_args:
        if arg in cmd_arg:
            config_data["Ratelimiting"][arg] = cmd_arg[arg]
    for arg in runtime_args:
        if arg in cmd_arg:
            config_data["Runtime"][arg] = cmd_arg[arg]
    for arg in sorting_args:
        if arg in cmd_arg:
            config_data["Sorting"][arg] = cmd_arg[arg]
    return config_data


async def document_args(args: dict):
    """We document the runtime arguments for debugging and troubleshooting, redacting sensitive information"""
    print_args = copy.deepcopy(args)
    print_args['Authentication']['xbunker_password'] = '!REDACTED!' if args['Authentication']['xbunker_password'] is not None else None
    print_args['Authentication']['socialmediagirls_password'] = '!REDACTED!' if args['Authentication']['socialmediagirls_password'] is not None else None
    print_args['Authentication']['simpcity_password'] = '!REDACTED!' if args['Authentication']['simpcity_password'] is not None else None
    print_args['Authentication']['pixeldrain_api_key'] = '!REDACTED!' if args['Authentication']['pixeldrain_api_key'] is not None else None
    print_args['JDownloader']['jdownloader_password'] = '!REDACTED!' if args['JDownloader']['jdownloader_password'] is not None else None

    await log("Starting Cyberdrop-DL")
    await log(f"Using authentication arguments: {print_args['Authentication']}", quiet=True)
    await log(f"Using file arguments: {print_args['Files']}", quiet=True)
    await log(f"Using forum option arguments: {print_args['Forum_Options']}", quiet=True)
    await log(f"Using ignore arguments: {print_args['Ignore']}", quiet=True)
    await log(f"Using jdownloader arguments: {print_args['JDownloader']}", quiet=True)
    await log(f"Using progress option arguments: {print_args['Progress_Options']}", quiet=True)
    await log(f"Using ratelimiting arguments: {print_args['Ratelimiting']}", quiet=True)
    await log(f"Using runtime arguments: {print_args['Runtime']}", quiet=True)
    await log(f"Using sorting arguments: {print_args['Sorting']}", quiet=True)
