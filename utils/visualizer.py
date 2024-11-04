import os
import pandas as pd
import logging
import plotly.graph_objs as go


class Visualizer:
    @classmethod
    def visualize(cls, df_stage_combined: pd.DataFrame, df_stability_combined: pd.DataFrame, folder_name: str):
        logging.info('Start generating visualizations.')
        if not df_stage_combined.empty:
            cls.plot_performance(df_stage_combined, os.path.join(folder_name, 'graphs', 'Stage'), 'Stage')
        else:
            logging.warning("Stage DataFrame is empty. Skipping visualization for Stage.")

        if not df_stability_combined.empty:
            cls.plot_performance(df_stability_combined, os.path.join(folder_name, 'graphs', 'Stability'), 'Stability')
        else:
            logging.warning("Stability DataFrame is empty. Skipping visualization for Stability.")

        logging.info('Visualizations generated.')

    @classmethod
    def plot_performance(cls, df: pd.DataFrame, folder_name: str, df_name: str):
        metrics = df.columns.get_level_values(2).unique().tolist()
        steps = df.columns.get_level_values(0).unique()
        files = df.columns.get_level_values(1).unique()

        os.makedirs(folder_name, exist_ok=True)

        for step in steps:
            for metric in metrics:
                if metric == 'Time':
                    continue

                for file in files:
                    if (step, file, 'Time') in df.columns and (step, file, metric) in df.columns:
                        time = df[(step, file, 'Time')].copy()
                        data = df[(step, file, metric)].copy()

                        df_combined = pd.DataFrame({'Time': time, metric: data})

                        df_combined.dropna(inplace=True)
                        df_combined.drop_duplicates(subset='Time', inplace=True)
                        df_combined.reset_index(drop=True, inplace=True)

                    else:
                        logging.warning(f"Time or metric '{metric}' column not found for {file} at {step}.")

                filename_png = f'{step}_{df_name}_{metric}.png'
                filepath_png = os.path.join(folder_name, filename_png)

                fig = go.Figure()

                for file in files:
                    if (step, file, 'Time') in df.columns and (step, file, metric) in df.columns:
                        time = df[(step, file, 'Time')].copy()
                        data = df[(step, file, metric)].copy()

                        df_combined = pd.DataFrame({'Time': time, metric: data})

                        df_combined.dropna(inplace=True)
                        df_combined.drop_duplicates(subset='Time', inplace=True)
                        df_combined.reset_index(drop=True, inplace=True)

                        if not df_combined.empty:
                            fig.add_trace(go.Scatter(
                                x=df_combined['Time'],
                                y=df_combined[metric],
                                mode='lines',
                                name=file,
                                line=dict(width=2)
                            ))
                        else:
                            logging.warning(f"Data is empty after cleaning for {file} at {step}.")
                    else:
                        logging.warning(f"Time or metric '{metric}' column not found for {file} at {step}.")

                fig.update_layout(
                    title=f'{metric} at {step} ({df_name})',
                    xaxis_title='Time',
                    yaxis_title=metric,
                    legend_title='Files',
                    template='plotly_dark',
                    hovermode='x unified'
                )

                filename_html = f'{step}_{df_name}_{metric}.html'
                filepath_html = os.path.join(folder_name, filename_html)

                fig.write_html(filepath_html)
                fig.write_image(filepath_png, width=1920, height=1080)

        for metric in metrics:
            if metric == 'Time':
                continue

            all_time = {}
            all_data = {}

            for file in files:
                all_time[file] = []
                all_data[file] = []
                cumulative_time = 0

                for step in steps:
                    if (step, file, 'Time') in df.columns and (step, file, metric) in df.columns:
                        time = df[(step, file, 'Time')].copy()
                        data = df[(step, file, metric)].copy()

                        df_combined = pd.DataFrame({'Time': time, metric: data})

                        df_combined.dropna(inplace=True)
                        df_combined.drop_duplicates(subset='Time', inplace=True)
                        df_combined.reset_index(drop=True, inplace=True)

                        if not df_combined.empty:
                            time_duration = df_combined['Time'].iloc[-1] - df_combined['Time'].iloc[0] + 1

                            df_combined['Time'] += cumulative_time

                            cumulative_time += time_duration

                            all_time[file].append(df_combined['Time'])
                            all_data[file].append(df_combined[metric])
                        else:
                            logging.warning(f"Data is empty after cleaning for {file} at {step}.")
                    else:
                        logging.warning(f"Time or metric '{metric}' column not found for {file} at {step}.")

            filename_png = f'All_Steps_{df_name}_{metric}.png'
            filepath_png = os.path.join(folder_name, filename_png)

            fig = go.Figure()

            for file in files:
                if all_time[file] and all_data[file]:
                    concatenated_time = pd.concat(all_time[file]).reset_index(drop=True)
                    concatenated_data = pd.concat(all_data[file]).reset_index(drop=True)

                    if len(concatenated_time) == len(concatenated_data):
                        fig.add_trace(go.Scatter(
                            x=concatenated_time,
                            y=concatenated_data,
                            mode='lines',
                            name=file,
                            line=dict(width=2)
                        ))
                    else:
                        logging.warning(f"Final data and time length mismatch for {file} in All Steps.")
                else:
                    logging.warning(f"No data to plot for {file} for metric {metric} in All Steps.")

            fig.update_layout(
                title=f'{metric} over all steps ({df_name})',
                xaxis_title='Time',
                yaxis_title=metric,
                legend_title='Files',
                template='plotly_dark',
                hovermode='x unified'
            )

            filename_html = f'All_Steps_{df_name}_{metric}.html'
            filepath_html = os.path.join(folder_name, filename_html)

            fig.write_html(filepath_html)
            fig.write_image(filepath_png, width=1920, height=1080)
