import datetime
import logging
import os.path
import socket
from abc import ABC
from typing import Optional, List, Dict

import dpkt
import yaml

from models.test_types import TestTypes
from utils.logger import Logger


class PcapStatistic:
    """
    Class responsible for calculating the --unique-ip-loops parameter.
    """

    def __init__(self, pcap_file: str, base_speed: float, total_sessions_per_min: int, percentage: float, is_pps: bool):
        """
        Initialize the calculator with necessary parameters.

        Args:
            pcap_file (str): Path to the pcap file.
            base_speed (float): Base speed considered as 100%.
            total_sessions_per_min (int): Desired total number of sessions at 100% load.
            percentage (float): Percentage of load on this pcap file.
            is_pps (bool): Is PPS or MBPS speed.
        """
        packets_per_loop, sessions_per_loop, packets_size = self.get_packets_sessions_per_loop_and_packets_size(
            pcap_file)

        self.packets_size = packets_size
        self.sessions_per_loop = sessions_per_loop
        self.packets_per_loop = packets_per_loop

        self.percentage_speed = base_speed * (percentage / 100)
        self.percentage_sessions = int(total_sessions_per_min * (percentage / 100))

        if is_pps:
            self.loops_per_minute = (self.percentage_speed * 60) / self.packets_per_loop
        else:
            self.loops_per_minute = (self.percentage_speed * 1_000_000 * 60) / (self.packets_size * 8)

        unique_ip_loop = (self.sessions_per_loop * self.loops_per_minute) / self.percentage_sessions
        unique_ip_loop = max(1, int(unique_ip_loop))

        unique_sessions_per_minute = (self.sessions_per_loop * self.loops_per_minute) / unique_ip_loop
        if unique_sessions_per_minute < self.percentage_sessions:
            unique_ip_loop = max(1, unique_ip_loop - 1)

        self.loop_count = unique_ip_loop

    @classmethod
    def get_packets_sessions_per_loop_and_packets_size(cls, pcap_file):
        packets_per_loop = 0
        packets_size = 0
        sessions = set()

        with open(pcap_file, 'rb') as f:
            pcap = dpkt.pcap.Reader(f)
            for timestamp, buf in pcap:
                packets_per_loop += 1
                packets_size += len(buf)

                eth = dpkt.ethernet.Ethernet(buf)

                if not isinstance(eth.data, dpkt.ip.IP):
                    continue

                ip = eth.data
                src_ip = socket.inet_ntoa(ip.src)
                dst_ip = socket.inet_ntoa(ip.dst)

                if isinstance(ip.data, dpkt.tcp.TCP) or isinstance(ip.data, dpkt.udp.UDP):
                    transport = ip.data
                    src_port = transport.sport
                    dst_port = transport.dport
                    protocol = "TCP" if isinstance(ip.data, dpkt.tcp.TCP) else "UDP"

                    session_id = tuple(sorted([(src_ip, src_port), (dst_ip, dst_port)])) + (protocol,)

                    sessions.add(session_id)

        sessions_per_loop = len(sessions)

        return packets_per_loop, sessions_per_loop, packets_size


class RunConfig:
    def __init__(self, general_config: Dict, sudo_password: Optional[str]):
        self.netmap_mode: bool = general_config.get('netmap_mode', False)
        self.speed_check: bool = general_config.get('speed_check', False)
        self.speed_check_interval: int = general_config.get('speed_check_interval', 3)
        self.speed_threshold: float = float(general_config.get('speed_threshold', 1.2))
        self.is_sudo: bool = general_config.get('is_sudo', False)
        self.sudo_password: Optional[str] = sudo_password

        if self.speed_check_interval < 1:
            self.speed_check = False


class PcapConfig:
    def __init__(self, pcap_id: int, pcap_config: Dict, default_interface: str):
        self.file: str = pcap_config['file']
        self.percentage: float = float(pcap_config.get('percentage', 0))
        self.interface: str = pcap_config.get('interface', default_interface)
        self.loop_count: Optional[int] = pcap_config.get('loop_count', None)
        self.is_percent_loop_calculate: bool = pcap_config.get('is_percent_loop_calculate', False)
        self.preload_in_ram: bool = pcap_config.get('preload_in_ram', True)
        self.netmap_privilege: bool = pcap_config.get('netmap_privilege', False)
        self.is_pcap_with_netmap: bool = self.netmap_privilege
        self.pcap_statistic: Optional[PcapStatistic] = None
        self.pcap_id: int = pcap_id


class PcapConfigs:
    @staticmethod
    def get_pcap_configs_list(pcap_configs_list: List[Dict], is_netmap_mode: bool) -> List[PcapConfig]:
        default_interface: str = pcap_configs_list[0]['interface']
        pcap_configs: List[PcapConfig] = []

        for i, pcap_config in enumerate(pcap_configs_list):
            pcap_configs.append(PcapConfig(i, pcap_config, default_interface))

        if len(pcap_configs) > 1:
            percentage_sum = sum(pcap_config.percentage for pcap_config in pcap_configs)
            if percentage_sum != 100.0:
                raise ValueError(f'Percentage of pcap files is not equals 100.0: {percentage_sum}')
        else:
            pcap_configs[0].percentage = 100.0

        if is_netmap_mode:
            max_percentage = max(pcap_config.percentage for pcap_config in pcap_configs)
            is_privilege_mode = any(pcap_config.netmap_privilege for pcap_config in pcap_configs)

            if not is_privilege_mode:
                for pcap_config in pcap_configs:
                    if pcap_config.percentage == max_percentage:
                        pcap_config.is_pcap_with_netmap = True
                        break

        return pcap_configs


class TcpReplayArgsConfig:
    def __init__(self, tcpreplay_args: Dict):
        self.args_dict: Dict = tcpreplay_args


class BashScriptConfig:
    def __init__(self, bash_script: Dict):
        self.script: str = bash_script['script']
        self.only_once: bool = bash_script.get('only_once', False)
        self.is_before_stage: bool = bash_script.get('is_before_stage', True)

        self.run_count: int = 0


class BashScriptsConfig:
    def __init__(self, bash_scripts: List[Dict]):
        self.bash_scripts_list = []
        for bash_script in bash_scripts:
            self.bash_scripts_list.append(BashScriptConfig(bash_script))


class LoadConfig(ABC):
    def __init__(self, test_type: str, test_id: int, test_tag: str, load_config: Dict, test_folder: Optional[str]):
        self.steps: int = load_config.get('steps', 1)
        self.impact: int = load_config['impact']
        self.test_type: str = test_type
        self.test_id: int = test_id
        self.test_tag: str = test_tag

        if test_folder is None:
            time_now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.test_folder: str = os.path.join('load_tests',
                                                 self.test_type,
                                                 f'{self.test_id}__{self.test_tag}__{time_now}')
        else:
            self.test_folder: str = test_folder

        os.makedirs(self.test_folder, exist_ok=True)
        Logger.append_logger(self.test_folder)

        self.total_sessions_per_min: Optional[int] = load_config.get('total_sessions_per_min', None)

        if 'base_speed_pps' in load_config and 'base_speed_mbps' in load_config:
            raise ValueError('Only one parameter of speed can be in config!')
        elif 'base_speed_pps' in load_config:
            self.is_pps: bool = True
            self.base_speed: float = float(load_config['base_speed_pps'])
        elif 'base_speed_mbps' in load_config:
            self.is_pps: bool = False
            self.base_speed: float = float(load_config['base_speed_mbps'])
        else:
            raise ValueError('There is no speed param in load config!')


class MaxPerfLoadConfig(LoadConfig):
    def __init__(self, load_config: Dict, test_id: int, test_tag: str, test_folder: Optional[str]):
        super().__init__(TestTypes.MAX_PERF, test_id, test_tag, load_config, test_folder)
        self.step_duration: int = load_config['step_duration']
        self.start_speed_percent: float = float(load_config['start_speed_percent'])
        self.increment_percent: float = float(load_config['increment_percent'])


class StabilityLoadConfig(LoadConfig):
    def __init__(self, load_config: Dict, test_id: int, test_tag: str, test_folder: Optional[str]):
        super().__init__(TestTypes.STABILITY, test_id, test_tag, load_config, test_folder)
        self.step_duration: int = load_config['step_duration']
        self.step_percent: float = float(load_config['step_percent'])


class SpikeLoadConfig(LoadConfig):
    def __init__(self, pcap_configs: List[PcapConfig], load_config: Dict, test_id: int, test_tag: str,
                 test_folder: Optional[str]):
        super().__init__(TestTypes.SPIKE, test_id, test_tag, load_config, test_folder)
        self.spike_duration: int = load_config['spike_duration']
        self.stability_speed_duration: int = load_config['stability_speed_duration']
        self.stability_speed_percent: float = float(load_config['stability_speed_percent'])
        self.spike_base_percent: float = float(load_config['spike_base_percent'])
        self.increment_percent: float = float(load_config['increment_percent'])
        self.pcap_for_spike: Optional[list[PcapConfig]] = self.__get_pcap_spikes(
            load_config.get('pcap_for_spike', None), pcap_configs)

    @staticmethod
    def __get_pcap_spikes(pcap_files_list: Optional[List], pcap_configs: List[PcapConfig]) -> Optional[
        List[PcapConfig]]:
        if pcap_files_list is None:
            return

        pcap_spike: List[PcapConfig] = []

        for pcap_file in pcap_files_list:
            if not any(pcap_config.file == pcap_file for pcap_config in pcap_configs):
                raise ValueError(f'Spike pcap file "{pcap_file}" not in general config!')

            for pcap_config in pcap_configs:
                if pcap_config.file == pcap_file:
                    pcap_spike.append(pcap_config)
                    break

        return pcap_spike


class CustomLoadConfig(LoadConfig):
    def __init__(self, load_config: Dict, test_id: int, test_tag: str, test_folder: Optional[str]):
        super().__init__(TestTypes.CUSTOM, test_id, test_tag, load_config, test_folder)


class Config:
    def __init__(self, config_yaml_file: str, load_yaml_file: str, test_type: str, test_id: int,
                 test_tag: str, sudo_password: Optional[str], test_folder: Optional[str]):
        logging.info(
            f'Parsing yaml general config "{config_yaml_file}" '
            f'and load config "{load_yaml_file}" for test type "{test_type}"'
        )

        with open(config_yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        with open(load_yaml_file, 'r', encoding='utf-8') as f:
            load_config = yaml.safe_load(f)

        self.run_config: RunConfig = RunConfig(config.get('run_config', {}), sudo_password)
        self.bash_scripts_config: BashScriptsConfig = BashScriptsConfig(config.get('bash_scripts_config', []))
        self.pcap_configs: List[PcapConfig] = PcapConfigs.get_pcap_configs_list(config['pcap_files'],
                                                                                self.run_config.netmap_mode)

        self.tcpreplay_args: TcpReplayArgsConfig = TcpReplayArgsConfig(config.get('tcpreplay_args', {}))
        self.load_config: LoadConfig

        if test_type == TestTypes.MAX_PERF:
            self.load_config = MaxPerfLoadConfig(load_config[TestTypes.MAX_PERF], test_id, test_tag, test_folder)
        elif test_type == TestTypes.STABILITY:
            self.load_config = StabilityLoadConfig(load_config[TestTypes.STABILITY], test_id, test_tag, test_folder)
        elif test_type == TestTypes.SPIKE:
            self.load_config = SpikeLoadConfig(self.pcap_configs, load_config[TestTypes.SPIKE], test_id, test_tag,
                                               test_folder)
        elif test_type == TestTypes.CUSTOM:
            self.load_config = CustomLoadConfig(load_config[TestTypes.CUSTOM], test_id, test_tag, test_folder)
            raise ValueError("Custom test type is not implemented yet.")
        else:
            raise ValueError(f"Unknown test type: {test_type}")

        self.__calculate_loops()

        logging.info(
            f'Parsing yaml finished! Configuration:\n'
            f'{yaml.dump(self.__convert_to_dict(self), default_flow_style=False)}'
        )

    def __calculate_loops(self):
        for pcap_config in self.pcap_configs:
            if pcap_config.loop_count is None and self.load_config.total_sessions_per_min is not None:
                pcap_config.pcap_statistic = PcapStatistic(
                    pcap_file=pcap_config.file,
                    base_speed=self.load_config.base_speed,
                    total_sessions_per_min=self.load_config.total_sessions_per_min,
                    percentage=pcap_config.percentage,
                    is_pps=self.load_config.is_pps
                )

                pcap_config.loop_count = pcap_config.pcap_statistic.loop_count
            elif pcap_config.loop_count is None and self.load_config.total_sessions_per_min is None:
                pcap_config.loop_count = 0
                pcap_config.is_percent_loop_calculate = False

    @staticmethod
    def __convert_to_dict(obj):
        hide_vars = ['sudo_password']
        if isinstance(obj, list):
            return [Config.__convert_to_dict(item) for item in obj if not item in hide_vars]
        elif hasattr(obj, '__dict__'):
            return {key: Config.__convert_to_dict(value) for key, value in obj.__dict__.items() if not key in hide_vars}
        else:
            return obj
