import argparse
import os.path
from typing import Optional

from models.test_types import TestTypes


class ArgsParser:
    def __init__(self):
        args = self.__parse_args()

        self.config: str = args.config
        self.load: str = args.load
        self.sudo_password: str = args.sudo_password
        self.test_folder: Optional[str] = args.test_folder
        self.test_id: int = args.test_id
        self.test_tag: str = args.test_tag
        self.test_type: str = args.test_type

    @staticmethod
    def __parse_args():
        """
        Parse command line arguments.

        Returns:
            argparse.Namespace: Parsed arguments.
        """
        parser = argparse.ArgumentParser(description='PcapBlaster TCPReplay Test Runner')
        parser.add_argument('-c', '--config', type=str, default=os.path.join('config', 'config.yaml'),
                            help='Path to the config file. (default=config/config.yaml)')
        parser.add_argument('-l', '--load', type=str, default=os.path.join('config', 'load.yaml'),
                            help='Path to the load config file. (default=config/load.yaml)')
        parser.add_argument('-p', '--sudo_password', type=str, default=os.getenv('SUDO_PASS', None),
                            help='Password for SUDO')
        parser.add_argument('-f', '--test_folder', type=str,
                            help='Folder of test to create report without starting test')
        parser.add_argument('-i', '--test_id', type=int, default=-1, help='ID of test')
        parser.add_argument('-t', '--test_tag', type=str, default='DEBUG', help='Tag of test')
        parser.add_argument('-T', '--test_type', type=str, required=True, choices=TestTypes.TEST_TYPES,
                            help=f'Type of test to run ({", ".join(TestTypes.TEST_TYPES)})')
        args = parser.parse_args()

        return args
