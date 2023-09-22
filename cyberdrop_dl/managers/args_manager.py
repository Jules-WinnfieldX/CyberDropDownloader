from __future__ import annotations

from cyberdrop_dl.utils.args.args import parse_args


class ArgsManager:
    def __init__(self):
        self.parsed_args = {}

        self.all_configs = False
        self.immediate_download = False
        self.load_config_from_args = False
        self.load_config_name = ""
        self.portable = False

        self.other_links: list = []

    def startup(self) -> None:
        self.parsed_args = parse_args().__dict__

        self.immediate_download = self.parsed_args['download']
        self.all_configs = self.parsed_args['download_all_configs']
        self.load_config_name = self.parsed_args['config']

        if self.load_config_name:
            self.load_config_from_args = True
        self.portable = self.parsed_args['portable']

        self.other_links = self.parsed_args['links']

        del self.parsed_args['download']
        del self.parsed_args['download_all_configs']
        del self.parsed_args['config']
        del self.parsed_args['portable']
        del self.parsed_args['links']

