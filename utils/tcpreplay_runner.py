import os
import subprocess
import threading
import time
import logging
from typing import Optional

from models.config import Config, MaxPerfLoadConfig, StabilityLoadConfig, SpikeLoadConfig, CustomLoadConfig, \
    PcapConfig, RunConfig, TcpReplayArgsConfig


class TcpreplayRunner:
    """
    Class responsible for running tcpreplay with the given configuration.
    """

    def __init__(self, config: Config):
        """
        Initialize the runner with the configuration.

        Args:
            config (Config): Configuration dictionary.
        """
        self.config: Config = config

    def run(self):
        """
        Run the tcpreplay tests based on the configuration.
        """
        logging.info('Starting test run.')

        if isinstance(self.config.load_config, MaxPerfLoadConfig):
            self.run_max_perf_test()
        elif isinstance(self.config.load_config, StabilityLoadConfig):
            self.run_stability_test()
        elif isinstance(self.config.load_config, SpikeLoadConfig):
            self.run_spike_test()
        elif isinstance(self.config.load_config, CustomLoadConfig):
            raise ValueError("Custom test type is not implemented yet.")
        else:
            raise ValueError("Unknown test type.")

        logging.info('Test run completed.')

    def run_max_perf_test(self):
        """
        Run the max_perf test type.
        """
        load_params: MaxPerfLoadConfig = self.config.load_config

        for step_number in range(1, load_params.steps + 1):
            logging.info(f"Starting step {step_number}")

            current_load_percent = load_params.start_speed_percent + load_params.increment_percent * (step_number - 1)

            step_thread = StepThread(
                step_number=step_number,
                pcap_configs=self.config.pcap_configs,
                run_config=self.config.run_config,
                tcpreplay_args=self.config.tcpreplay_args,
                current_load_percent=current_load_percent,
                base_speed=load_params.base_speed,
                is_pps=load_params.is_pps,
                step_duration=load_params.step_duration,
                impact=load_params.impact,
                total_sessions_per_min=load_params.total_sessions_per_min,
                test_folder=self.config.load_config.test_folder
            )

            step_thread.start()
            step_thread.join()

            logging.info(f"Ending step {step_number}")

    def run_stability_test(self):
        """
        Run the stability test type.
        """
        load_params: StabilityLoadConfig = self.config.load_config

        logging.info("Starting stability test")

        step_thread = StepThread(
            step_number=1,
            pcap_configs=self.config.pcap_configs,
            run_config=self.config.run_config,
            tcpreplay_args=self.config.tcpreplay_args,
            current_load_percent=load_params.step_percent,
            base_speed=load_params.base_speed,
            is_pps=load_params.is_pps,
            step_duration=load_params.step_duration,
            impact=load_params.impact,
            total_sessions_per_min=load_params.total_sessions_per_min,
            test_folder=self.config.load_config.test_folder
        )

        step_thread.start()
        step_thread.join()

        logging.info("Ending stability test")

    def run_spike_test(self):
        """
        Run the spike test type.
        """
        load_params: SpikeLoadConfig = self.config.load_config

        for step in range(1, load_params.steps + 1):
            # Stability period
            logging.info(f"Starting stability period for step {step}")

            step_thread = StepThread(
                step_number=(step * 2) - 1,
                pcap_configs=self.config.pcap_configs,
                run_config=self.config.run_config,
                tcpreplay_args=self.config.tcpreplay_args,
                current_load_percent=load_params.stability_speed_percent,
                base_speed=load_params.base_speed,
                is_pps=load_params.is_pps,
                step_duration=load_params.stability_speed_duration,
                impact=load_params.impact,
                total_sessions_per_min=load_params.total_sessions_per_min,
                test_folder=self.config.load_config.test_folder
            )

            step_thread.start()
            step_thread.join()

            logging.info(f"Ending stability period for step {step}")

            # Spike period
            logging.info(f"Starting spike period for step {step}")

            current_spike_percent = load_params.spike_base_percent + load_params.increment_percent * (step - 1)

            step_thread = StepThread(
                step_number=step * 2,
                pcap_configs=self.config.pcap_configs,
                run_config=self.config.run_config,
                tcpreplay_args=self.config.tcpreplay_args,
                current_load_percent=load_params.stability_speed_percent,
                spike_load_percent=current_spike_percent,
                pcap_for_spike=load_params.pcap_for_spike,
                base_speed=load_params.base_speed,
                is_pps=load_params.is_pps,
                step_duration=load_params.spike_duration,
                impact=load_params.impact,
                total_sessions_per_min=load_params.total_sessions_per_min,
                test_folder=self.config.load_config.test_folder
            )

            step_thread.start()
            step_thread.join()

            logging.info(f"Ending spike period for step {step}")


class StepThread(threading.Thread):
    """
    Thread class for running a single test step.
    """

    def __init__(self, step_number: int, pcap_configs: list[PcapConfig], run_config: RunConfig,
                 tcpreplay_args: TcpReplayArgsConfig, current_load_percent: float, base_speed: float, is_pps: bool,
                 step_duration: int, impact: int, total_sessions_per_min: int, test_folder: str,
                 spike_load_percent: Optional[float] = None, pcap_for_spike: Optional[list[PcapConfig]] = None):
        super().__init__()
        self.step_number = step_number
        self.pcap_configs = pcap_configs
        self.run_config = run_config
        self.tcpreplay_args = tcpreplay_args
        self.current_load_percent = current_load_percent
        self.base_speed = base_speed
        self.is_pps = is_pps
        self.step_duration = step_duration
        self.impact = impact
        self.total_sessions_per_min = total_sessions_per_min
        self.test_folder = test_folder

        self.spike_load_percent = spike_load_percent
        self.pcap_for_spike = pcap_for_spike

    def run(self):
        """
        Run the test step.
        """
        threads = []
        for pcap_config in self.pcap_configs:
            # Determine if this pcap should use spike load percent
            if self.pcap_for_spike and pcap_config.file in self.pcap_for_spike and self.spike_load_percent is not None:
                load_percent = self.spike_load_percent
            else:
                load_percent = self.current_load_percent

            runner = TcpreplayThread(
                step_number=self.step_number,
                pcap_config=pcap_config,
                run_config=self.run_config,
                tcpreplay_args=self.tcpreplay_args,
                load_percent=load_percent,
                base_speed=self.base_speed,
                is_pps=self.is_pps,
                step_duration=self.step_duration,
                impact=self.impact,
                total_sessions_per_min=self.total_sessions_per_min,
                test_folder=self.test_folder
            )

            runner.start()
            threads.append(runner)

        for t in threads:
            t.join()


class TcpreplayThread(threading.Thread):
    """
    Thread class for running tcpreplay for a single pcap file.
    """

    def __init__(self, step_number: int, pcap_config: PcapConfig, run_config: RunConfig,
                 tcpreplay_args: TcpReplayArgsConfig, load_percent: float, base_speed: float, is_pps: bool,
                 step_duration: int, impact: int, total_sessions_per_min: int, test_folder: str):
        super().__init__()
        self.step_number = step_number
        self.pcap_config = pcap_config
        self.run_config = run_config
        self.tcpreplay_args = tcpreplay_args
        self.load_percent = load_percent
        self.base_speed = base_speed
        self.is_pps = is_pps
        self.step_duration = step_duration
        self.impact = impact
        self.total_sessions_per_min = total_sessions_per_min
        self.loop_count = pcap_config.loop_count
        self.is_percent_loop_calculate = pcap_config.is_percent_loop_calculate
        self.test_folder = test_folder

    def run(self):
        """
        Run tcpreplay for the given pcap file.
        """
        percentage = self.pcap_config.percentage
        pcap_file = self.pcap_config.file
        interface = self.pcap_config.interface
        current_speed = self.base_speed * (self.load_percent / 100)
        speed = current_speed * (percentage / 100)

        if self.is_percent_loop_calculate:
            if self.loop_count == 0:
                loops = self.loop_count
            else:
                calculated_loops = int(self.loop_count * (self.load_percent / 100))
                loops = max(0, calculated_loops)
        else:
            loops = self.loop_count

        stats_file = os.path.join(self.test_folder,
                                  f"stats__step_{self.step_number}__"
                                  f"file_num_{self.pcap_config.pcap_id}__"
                                  f"{os.path.basename(pcap_file)}.log")
        stats_err_file = os.path.join(self.test_folder,
                                      f"err__step_{self.step_number}__"
                                      f"file_num_{self.pcap_config.pcap_id}__"
                                      f"{os.path.basename(pcap_file)}.log")
        duration = self.step_duration + self.impact

        runner = TcpreplayProcessRunner(
            pcap_file=pcap_file,
            interface=interface,
            speed=speed,
            is_pps=self.is_pps,
            unique_ip_loops=loops,
            tcpreplay_args=self.tcpreplay_args,
            stats_file=stats_file,
            stats_err_file=stats_err_file,
            netmap_mode=self.pcap_config.is_pcap_with_netmap,
            duration=duration,
            speed_check=self.run_config.speed_check,
            speed_check_interval=self.run_config.speed_check_interval,
            speed_threshold=self.run_config.speed_threshold,
            preload_in_ram=self.pcap_config.preload_in_ram,
            is_sudo=self.run_config.is_sudo,
            sudo_password=self.run_config.sudo_password
        )

        runner.run()


class TcpreplayProcessRunner:
    """
    Class for managing the tcpreplay process.
    """

    def __init__(self, pcap_file: str, interface: str, speed: float, is_pps: bool, unique_ip_loops: int,
                 tcpreplay_args: TcpReplayArgsConfig, stats_file: str, stats_err_file: str, netmap_mode: bool,
                 duration: int, speed_check: bool, speed_check_interval: int, speed_threshold: float,
                 preload_in_ram: bool, is_sudo: bool, sudo_password: Optional[str]):
        """
        Initialize the process runner with necessary parameters.
        """
        self.pcap_file = pcap_file
        self.interface = interface
        self.speed = speed
        self.is_pps = is_pps
        self.unique_ip_loops = unique_ip_loops
        self.tcpreplay_args = tcpreplay_args
        self.stats_file = stats_file
        self.stats_err_file = stats_err_file
        self.netmap_mode = netmap_mode
        self.duration = duration
        self.speed_check = speed_check
        self.speed_check_interval = speed_check_interval
        self.speed_threshold = speed_threshold
        self.preload_in_ram = preload_in_ram
        self.is_sudo = is_sudo
        self.sudo_password = sudo_password

    def run(self):
        """
        Run the tcpreplay process with monitoring and restarting if necessary.
        """
        cmd = []
        if self.is_sudo:
            cmd = ['sudo', '-k', '-S']

        cmd.extend([
            'tcpreplay',
            '-i', self.interface,
            '--stats=1',
            '--loop=0',
            f'--duration={self.duration}',
        ])

        if self.preload_in_ram:
            cmd.append('--preload-pcap')

        if self.unique_ip_loops:
            cmd.append('--unique-ip')

            if self.unique_ip_loops > 0:
                cmd.append(f'--unique-ip-loops={self.unique_ip_loops}')

        if self.is_pps:
            cmd.append(f'--pps={self.speed}')
            log_str = 'PPS'
        else:
            cmd.append(f'--mbps={self.speed}')
            log_str = 'MBPS'

        if self.netmap_mode:
            cmd.extend(['--netmap', '--nm-delay=2'])

        if self.tcpreplay_args:
            for arg, value in self.tcpreplay_args.args_dict.items():
                if value is None:
                    cmd.append(f'--{arg}')
                elif isinstance(value, list):
                    cmd.append(f'--{arg}')
                    cmd.extend(value)
                else:
                    cmd.append(f'--{arg}={value}')

        cmd.append(self.pcap_file)

        logging.info(f"Executing command for {self.pcap_file}:\n{' '.join(cmd)}")

        start_time = int(time.time())
        start_time_str = str(start_time) + '\n'
        last_check_time = start_time
        unstable = False
        time_log_sec = 0

        with open(self.stats_file, 'a') as stat_file:
            while True:
                with (subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True) as process):
                    if self.is_sudo:
                        process.stdin.write(self.sudo_password + '\n')
                        process.stdin.flush()

                    stat_file.write(start_time_str)
                    stat_file.flush()

                    stderr_thread = threading.Thread(target=self.__read_stderr, args=(process, self.stats_err_file))
                    stderr_thread.start()

                    for line in process.stdout:
                        stat_file.write(line)
                        stat_file.flush()

                        if self.speed_check:
                            current_time = int(time.time())
                            elapsed_time = current_time - start_time

                            if line.__contains__('Actual:'):
                                time_log_sec = int(float(line.split()[-2]))

                                if time_log_sec < elapsed_time + (5 if self.netmap_mode else 3):
                                    continue
                            elif line.__contains__('Rated:'):
                                if time_log_sec < elapsed_time:
                                    continue

                                parts = line.split(", ")
                                if self.is_pps:
                                    speed = float(parts[1].split(' ')[0])
                                else:
                                    speed = float(parts[2].split(' ')[0])
                            else:
                                continue

                            if self.__calculate_threshold(current_time, last_check_time, speed):
                                last_check_time = current_time
                                logging.warning(f'Detected abnormal {log_str} rate, restarting tcpreplay')

                                if self.is_sudo:
                                    subproc = subprocess.Popen(['sudo', 'kill', str(process.pid)],
                                                               stdin=subprocess.PIPE,
                                                               stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE,
                                                               text=True)
                                    subproc.stdin.write(self.sudo_password + '\n')
                                    subproc.stdin.flush()
                                else:
                                    process.terminate()

                                unstable = True
                                break

                            last_check_time = current_time

                        if int(time.time()) - start_time >= self.duration + 5 and process.poll() is None:
                            if self.is_sudo:
                                subproc = subprocess.Popen(['sudo', 'kill', str(process.pid)],
                                                           stdin=subprocess.PIPE,
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE,
                                                           text=True)
                                subproc.stdin.write(self.sudo_password + '\n')
                                subproc.stdin.flush()
                            else:
                                process.terminate()

                            break

                stderr_thread.join()

                if not unstable:
                    stat_file.write(str(int(time.time())))
                    stat_file.flush()

                    break  # Exit if tcpreplay finished normally
                else:
                    unstable = False  # Reset unstable flag and restart tcpreplay
                    time.sleep(1)  # Delay before restarting

    def __calculate_threshold(self, current_time, last_check_time, speed):
        check_time = current_time - last_check_time

        if check_time >= self.speed_check_interval:

            if speed >= self.speed * self.speed_threshold or speed <= self.speed * -self.speed_threshold:
                return True
            else:
                return False

        else:
            return False

    @staticmethod
    def __read_stderr(proc, stat_err_file_path) -> Optional[str]:
        with open(stat_err_file_path, 'a') as err_file:
            for line in proc.stderr:
                err_file.write(line)
                err_file.flush()

                if line.__contains__('Fatal Error:'):
                    return line
