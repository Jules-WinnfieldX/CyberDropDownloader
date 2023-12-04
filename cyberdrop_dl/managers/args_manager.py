from __future__ import annotations

from cyberdrop_dl.utils.args.args import parse_args


class ArgsManager:
    def __init__(self):
        self.parsed_args = {}

        self.all_configs = False
        self.retry = False

        self.immediate_download = False
        self.load_config_from_args = False
        self.load_config_name = ""
        self.portable = False

        self.other_links: list = []

    def startup(self) -> None:
        """Parses arguments and sets variables accordingly"""
        if self.parsed_args:
            return

        self.parsed_args = parse_args().__dict__

        self.immediate_download = self.parsed_args['download']
        self.load_config_name = self.parsed_args['config']

        if self.parsed_args['download_all_configs']:
            self.all_configs = True
            self.immediate_download = True

        if self.load_config_name:
            self.load_config_from_args = True
        self.portable = self.parsed_args['portable']

        self.other_links = self.parsed_args['links']

        del self.parsed_args['download']
        del self.parsed_args['download_all_configs']
        del self.parsed_args['config']
        del self.parsed_args['portable']
        del self.parsed_args['links']
