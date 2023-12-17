from __future__ import annotations

from cyberdrop_dl.utils.args.args import parse_args


class ArgsManager:
    def __init__(self):
        self.parsed_args = {}

        self.all_configs = False
        self.retry = False

        self.immediate_download = False
        self.no_ui = False
        self.load_config_from_args = False
        self.load_config_name = ""

        self.other_links: list = []

        # Files
        self.input_file = None
        self.download_dir = None
        self.config_file = None
        self.appdata_dir = None

    def startup(self) -> None:
        """Parses arguments and sets variables accordingly"""
        if self.parsed_args:
            return

        self.parsed_args = parse_args().__dict__

        self.immediate_download = self.parsed_args['download']
        self.load_config_name = self.parsed_args['config']

        if self.parsed_args['no_ui']:
            self.immediate_download = True
            self.no_ui = True

        if self.load_config_name:
            self.load_config_from_args = True

        if self.parsed_args['download_all_configs']:
            self.all_configs = True
            self.immediate_download = True

        if self.parsed_args['retry_failed']:
            self.retry = True
            self.immediate_download = True

        if self.parsed_args['input_file']:
            self.input_file = self.parsed_args['input_file']
        if self.parsed_args['output_folder']:
            self.download_dir = self.parsed_args['output_folder']
        if self.parsed_args['appdata_folder']:
            self.appdata_dir = self.parsed_args['appdata_folder']
        if self.parsed_args['config_file']:
            self.config_file = self.parsed_args['config_file']
            self.immediate_download = True

        self.other_links = self.parsed_args['links']

        del self.parsed_args['download']
        del self.parsed_args['download_all_configs']
        del self.parsed_args['config']
        del self.parsed_args['links']
