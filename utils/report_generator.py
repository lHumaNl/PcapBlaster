import re
from datetime import datetime
from typing import List, Dict

import pandas as pd
import logging
import os

from models.config import Config


class ReportGenerator:
    """
    Class responsible for parsing statistics and generating reports.
    """

    def __init__(self, config: Config):
        """
        Initialize the report generator.

        Args:
            config (Config): Config of test.
        """
        self.config = config

        self.df_total_stability_combined = None
        self.df_stability_combined = None
        self.df_total_combined = None
        self.df_stage_combined = None

    def generate_report(self):
        """
        Generate an Excel report from parsed statistics.
        """
        logging.info('Start generating Excel report.')

        all_data = {}
        for step in range(1, self.config.load_config.steps + 1):
            all_data[step] = {}
            for pcap_config in self.config.pcap_configs:
                file_name = f"{os.path.basename(pcap_config.file)}.log"
                stats_file = os.path.join(self.config.load_config.test_folder,
                                          f"stats__step_{step}__"
                                          f"file_num_{pcap_config.pcap_id}__"
                                          f"{file_name}")

                parser = StatsParser(stats_file)
                df_stage, df_total, df_stability, df_total_stability = parser.parse(self.config.load_config.impact)

                all_data[step][pcap_config.pcap_id] = {
                    'Stage': df_stage,
                    'Total': df_total,
                    'Stability': df_stability,
                    'Total stability': df_total_stability,
                    'file_name': file_name.replace('.log', '')
                }

        if all_data:
            df_stage_combined = pd.DataFrame()
            df_total_combined = pd.DataFrame()
            df_stability_combined = pd.DataFrame()
            df_total_stability_combined = pd.DataFrame()

            for step, files_data in all_data.items():
                num_files = len(files_data)
                stage_summary_list = []
                stability_summary_list = []
                total_summary_list = []
                total_stability_summary_list = []

                step_level = ''
                for file_id, data in files_data.items():
                    step_level = f"Step {step}"
                    file_level = f"File {file_id + 1} - {data['file_name']}"

                    df_stage = data['Stage'].copy()
                    arrays = [
                        [step_level] * len(df_stage.columns),
                        [file_level] * len(df_stage.columns),
                        df_stage.columns
                    ]
                    df_stage.columns = pd.MultiIndex.from_arrays(arrays)
                    df_stage_combined = pd.concat([df_stage_combined, df_stage], axis=1)

                    if num_files > 1:
                        stage_summary_list.append(df_stage)

                    df_stability = data['Stability'].copy()
                    arrays = [
                        [step_level] * len(df_stability.columns),
                        [file_level] * len(df_stability.columns),
                        df_stability.columns
                    ]
                    df_stability.columns = pd.MultiIndex.from_arrays(arrays)
                    df_stability_combined = pd.concat([df_stability_combined, df_stability], axis=1)

                    if num_files > 1:
                        stability_summary_list.append(df_stability)

                    df_total = data['Total'].copy()
                    df_total.index = pd.MultiIndex.from_tuples(
                        [(step_level, file_level)],
                        names=['Step', 'File']
                    )
                    df_total_combined = pd.concat([df_total_combined, df_total])

                    if num_files > 1:
                        total_summary_list.append(df_total)

                    df_total_stability = data['Total stability'].copy()
                    df_total_stability.index = pd.MultiIndex.from_tuples(
                        [(step_level, file_level)],
                        names=['Step', 'File']
                    )
                    df_total_stability_combined = pd.concat([df_total_stability_combined, df_total_stability])

                    if num_files > 1:
                        total_stability_summary_list.append(df_total_stability)

                if num_files > 1:
                    df_stage_summary = self._create_summary_dataframe(stage_summary_list, step_level)
                    df_stage_combined = pd.concat([df_stage_combined, df_stage_summary], axis=1)

                    df_stability_summary = self._create_summary_dataframe(stability_summary_list, step_level)
                    df_stability_combined = pd.concat([df_stability_combined, df_stability_summary], axis=1)

                    df_total_summary = self._create_total_summary_dataframe(total_summary_list, df_stage_summary,
                                                                            step_level)
                    df_total_combined = pd.concat([df_total_combined, df_total_summary])

                    df_total_stability_summary = self._create_total_summary_dataframe(total_stability_summary_list,
                                                                                      df_stability_summary, step_level)
                    df_total_stability_combined = pd.concat([df_total_stability_combined, df_total_stability_summary])

            report_name = os.path.join(self.config.load_config.test_folder, 'report.xlsx')

            with pd.ExcelWriter(report_name) as writer:
                df_stage_combined.to_excel(writer, sheet_name='Stage')
                df_total_combined.to_excel(writer, sheet_name='Total')
                df_stability_combined.to_excel(writer, sheet_name='Stability')
                df_total_stability_combined.to_excel(writer, sheet_name='Total Stability')

            self.df_stage_combined = df_stage_combined
            self.df_total_combined = df_total_combined
            self.df_stability_combined = df_stability_combined
            self.df_total_stability_combined = df_total_stability_combined

            logging.info('Excel report generated.')
        else:
            logging.error("No data collected to generate report.")

    @staticmethod
    def _create_summary_dataframe(df_list, step_level):
        time_values = set()
        for df in df_list:
            time_cols = [
                col
                for col in df.columns
                if col[2] == 'Time'
            ]

            if time_cols:
                time_col = time_cols[0]
                time_values.update(df[time_col].tolist())
            else:
                logging.error(f"DataFrame is missing 'Time' column. Available columns: {df.columns}")
                continue

        time_values = sorted(time_values)

        if not time_values:
            logging.error("No 'Time' values available to create the summary DataFrame.")

            return pd.DataFrame()

        summary_df = pd.DataFrame({'Time': time_values})
        summary_df.set_index('Time', inplace=True)
        metric_cols = ['Packets', 'Bytes', 'Mbps', 'PPS']
        summary_metrics = pd.DataFrame(index=summary_df.index)

        for df in df_list:
            time_col = [
                col
                for col in df.columns
                if col[2] == 'Time'
            ][0]
            df_temp = df.set_index(time_col)
            df_temp.index.name = 'Time'
            cols = [
                col
                for col in df_temp.columns
                if col[2] in metric_cols
            ]
            df_temp = df_temp[cols]
            df_temp.columns = [col[2] for col in df_temp.columns]

            if df_temp.index.has_duplicates:
                df_temp = df_temp[~df_temp.index.duplicated(keep='first')]

            df_temp = df_temp.reindex(summary_df.index, fill_value=0)
            summary_metrics = summary_metrics.add(df_temp, fill_value=0)

        summary_metrics.reset_index(inplace=True)
        summary_level = 'Summary'
        arrays = [
            [step_level] * len(summary_metrics.columns),
            [summary_level] * len(summary_metrics.columns),
            summary_metrics.columns
        ]

        summary_metrics.columns = pd.MultiIndex.from_arrays(arrays)

        return summary_metrics

    @staticmethod
    def _create_total_summary_dataframe(df_list, df_summary, step_level):
        summary_data = {}
        tcp_replay_count = sum(df['TCPReplay Start Count'].iloc[0] for df in df_list)
        summary_data['TCPReplay Start Count'] = [tcp_replay_count]

        cols = df_summary.columns

        step_summary_cols = [
            col
            for col in cols
            if col[0] == step_level and col[1] == 'Summary'
        ]

        df_metrics = df_summary[step_summary_cols].copy()
        df_metrics.columns = [col[2] for col in df_metrics.columns]

        summary_data['Total Packets'] = [df_metrics['Packets'].iloc[-1]]
        summary_data['Total Bytes'] = [df_metrics['Bytes'].iloc[-1]]

        summary_data['Total Time'] = [df_metrics['Time'].max()]

        summary_data['Average Mbps'] = [df_metrics['Mbps'].mean()]
        summary_data['Min Mbps'] = [df_metrics['Mbps'].min()]
        summary_data['Max Mbps'] = [df_metrics['Mbps'].max()]

        summary_data['Average PPS'] = [df_metrics['PPS'].mean()]
        summary_data['Min PPS'] = [df_metrics['PPS'].min()]
        summary_data['Max PPS'] = [df_metrics['PPS'].max()]

        summary_df = pd.DataFrame(summary_data)
        summary_level = 'Summary'
        summary_df.index = pd.MultiIndex.from_tuples(
            [(step_level, summary_level)],
            names=['Step', 'File']
        )

        return summary_df


class StatsParser:
    """
    Class for parsing tcpreplay statistics files.
    """

    def __init__(self, stats_file):
        """
        Initialize the parser.

        Args:
            stats_file (str): Path to the stats file.
        """
        self.stats_file = stats_file

    def parse(self, impact_time):
        """
        Parse the stats file and return DataFrames.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            - df_stage: DataFrame with all parsed statistics.
            - df_total: Summary DataFrame for total statistics.
            - df_stability: DataFrame for stability period.
            - df_total_stability: Summary DataFrame for stability period.
        """
        with open(self.stats_file, 'r') as stat_file:
            lines = stat_file.readlines()

        stage_start_timestamp = int(lines[0])
        stage_end_timestamp = int(lines[-1])

        test_start_count = 0
        total_packets = 0
        total_bytes = 0
        total_time = 0.0

        mbps_list = []
        pps_list = []

        data_entries: List[Dict] = []
        last_packets = 0
        last_bytes = 0
        last_time = 0
        end_time = None
        first_time = True

        for i, line in enumerate(lines[1:-1]):
            if line.startswith('Test start:'):
                test_start_count += 1

            elif line.startswith('Test complete:'):
                end_time_match = re.match(r'Test complete: (.+?)\.\d+', line)

                if end_time_match:
                    datetime_str = end_time_match.group(1)
                    end_time = int(datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S").timestamp())

            elif line.startswith('Actual:'):
                actual_match = re.match(r'Actual: (\d+) packets \((\d+) bytes\) sent in ([\d.+?]+) seconds', line)
                if actual_match:
                    packets = int(actual_match.group(1))
                    bytes_sent = int(actual_match.group(2))
                    time_sent = round(float(actual_match.group(3)))

                    if packets - total_packets == packets - last_packets or first_time:
                        total_packets = packets
                        total_bytes = bytes_sent
                        total_time = time_sent
                    else:
                        total_packets = packets + last_packets
                        total_bytes = bytes_sent + last_bytes
                        total_time = time_sent + last_time

                    first_time = False

                    data_entries.append({
                        'Packets': total_packets,
                        'Bytes': total_bytes,
                        'Time': total_time
                    })

                    last_packets = packets
                    last_bytes = bytes_sent
                    last_time = time_sent

            elif line.startswith('Rated:'):
                rated_match = re.match(r'Rated: [\d.+?]+ Bps, ([\d.+?]+) Mbps, ([\d.+?]+) pps', line)
                if rated_match:
                    mbps = float(rated_match.group(1))
                    pps = float(rated_match.group(2))

                    mbps_list.append(mbps)
                    pps_list.append(pps)

                    if data_entries:
                        data_entries[-1].update({
                            'Mbps': mbps,
                            'PPS': pps
                        })

        df_stage = pd.DataFrame(data_entries)

        df_total = pd.DataFrame(
            [
                {
                    'Total Packets': total_packets,
                    'Total Bytes': total_bytes,
                    'Total Time': total_time,
                    'Average Mbps': sum(mbps_list) / len(mbps_list) if mbps_list else 0,
                    'Min Mbps': min(mbps_list) if mbps_list else 0,
                    'Max Mbps': max(mbps_list) if mbps_list else 0,
                    'Average PPS': sum(pps_list) / len(pps_list) if pps_list else 0,
                    'Min PPS': min(pps_list) if pps_list else 0,
                    'Max PPS': max(pps_list) if pps_list else 0,
                    'TCPReplay Start Count': test_start_count
                }
            ]
        )

        if end_time and stage_end_timestamp - end_time < 5:
            stage_end_timestamp = end_time

        stage_duration = stage_end_timestamp - stage_start_timestamp
        offset = impact_time - (stage_duration - total_time)

        df_stability = df_stage[df_stage['Time'] >= offset].reset_index(drop=True)
        df_offset = df_stage[df_stage['Time'] < offset].reset_index(drop=True)

        if not df_offset.empty:
            last_packets = df_offset['Packets'].iloc[-1]
            last_bytes = df_offset['Bytes'].iloc[-1]
        else:
            last_packets = 0
            last_bytes = 0

        df_stability['Packets'] = df_stability['Packets'] - last_packets
        df_stability['Bytes'] = df_stability['Bytes'] - last_bytes
        df_stability['Time'] = df_stability['Time'] - df_stability['Time'].iloc[0] + 1

        if not df_stability.empty:
            total_packets_stability = df_stability['Packets'].iloc[-1]
            total_bytes_stability = df_stability['Bytes'].iloc[-1]
            total_time_stability = df_stability['Time'].iloc[-1]

            if 'Mbps' in df_stability.columns:
                mbps_list_stability = df_stability['Mbps']
                pps_list_stability = df_stability['PPS']
            else:
                mbps_list_stability = []
                pps_list_stability = []

            df_total_stability = pd.DataFrame(
                [
                    {
                        'Total Packets': total_packets_stability,
                        'Total Bytes': total_bytes_stability,
                        'Total Time': total_time_stability,
                        'Average Mbps': mbps_list_stability.mean() if len(mbps_list_stability) > 0 else 0,
                        'Min Mbps': mbps_list_stability.min() if len(mbps_list_stability) > 0 else 0,
                        'Max Mbps': mbps_list_stability.max() if len(mbps_list_stability) > 0 else 0,
                        'Average PPS': pps_list_stability.mean() if len(pps_list_stability) > 0 else 0,
                        'Min PPS': pps_list_stability.min() if len(pps_list_stability) > 0 else 0,
                        'Max PPS': pps_list_stability.max() if len(pps_list_stability) > 0 else 0,
                        'TCPReplay Start Count': test_start_count
                    }
                ]
            )
        else:
            df_total_stability = pd.DataFrame()

        return df_stage, df_total, df_stability, df_total_stability
