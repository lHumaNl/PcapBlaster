# PcapBlaster

PcapBlaster is a high-performance load testing tool that uses `tcpreplay` to replay packet capture (PCAP) files, monitor
load performance, and generate detailed reports. The reports are saved as Excel files with various performance metrics
and visualized through generated graphs.

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Arguments](#arguments)
6. [YAML Configuration](#yaml-configuration)
7. [Examples](#examples)

## Requirements

- Python 3.7 or higher
- `tcpreplay` installed and accessible in your PATH
- The following Python libraries (see `requirements.txt` for exact versions):
    - `pyyaml`
    - `dpkt`
    - `pandas`
    - `matplotlib`
    - `plotly`
    - `kaleido`
    - `numpy`
    - `openpyxl`

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/lHumaNl/PcapBlaster.git
    ```

2. Navigate to the project directory:
    ```bash
    cd pcapblaster
    ```

3. Set up the virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```

4. Install required packages:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

PcapBlaster uses two YAML configuration files:

- `config.yaml` for general configuration settings.
- `load.yaml` for defining load profiles and test parameters.

## Usage

Run PcapBlaster by providing the required arguments. Basic command structure:

python main.py --config path/to/config.yaml --load path/to/load.yaml --test_type [max_perf | stability | spike | custom]

### Arguments

The CLI arguments for `main.py` are as follows:

| Argument            | Description                                              | Default            |
|---------------------|----------------------------------------------------------|--------------------|
| -c, --config        | Path to the config file                                  | config/config.yaml |
| -l, --load          | Path to the load config file                             | config/load.yaml   |
| -p, --sudo_password | Password for sudo commands if necessary                  | None               |
| -f, --test_folder   | Directory to save test report without starting test      | None               |
| -i, --test_id       | ID of the test                                           | -1                 |
| -t, --test_tag      | Tag of the test                                          | DEBUG              |
| -T, --test_type     | Type of test to run (max_perf, stability, spike, custom) | Required           |

### YAML Configuration

#### config.yaml

The `config.yaml` file contains the main configuration settings for PcapBlaster. Key sections are:

| Parameter                   | Default  | Type       | Description                                                                                                                                                     |
|-----------------------------|----------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **run_config**              |          | Dictionary | General configuration for running the test.                                                                                                                     |
| - netmap_mode               | False    | Boolean    | Enables or disables netmap mode for high-performance packet replay.                                                                                             |
| - speed_check               | False    | Boolean    | Enables speed check during test execution to ensure target speed consistency.                                                                                   |
| - speed_check_interval      | 3        | Integer    | Interval in seconds between speed checks.                                                                                                                       |
| - speed_threshold           | 1.2      | Float      | Threshold multiplier for speed variance. If the speed deviates from the target by this factor, a warning is logged, and tcpreplay may restart.                  |
| - is_sudo                   | False    | Boolean    | Determines if sudo privileges are required for `tcpreplay` execution.                                                                                           |
| **pcap_files**              |          | List       | List of PCAP files to be replayed, each with specific settings.                                                                                                 |
| - file                      | Required | String     | Path to the PCAP file.                                                                                                                                          |
| - percentage                | 100.0    | Float      | Percentage load assigned to this PCAP file within the test. Percentages across all PCAP files must sum to 100%.                                                 |
| - interface                 | Required | String     | Network interface to use for replaying the PCAP file (e.g., `eth0`).                                                                                            |
| - loop_count                | None     | Integer    | Number of times to loop over this PCAP file. If None, the loop count is calculated based on speed and session parameters.                                       |
| - is_percent_loop_calculate | False    | Boolean    | Whether the loop count should be calculated as a percentage of the load, based on other parameters.                                                             |
| - preload_in_ram            | True     | Boolean    | If True, preloads the PCAP file into RAM for faster access.                                                                                                     |
| - netmap_privilege          | False    | Boolean    | Enables or disables netmap privileges.                                                                                                                          |
| **tcpreplay_args**          |          | Dictionary | Additional arguments passed to `tcpreplay`.                                                                                                                     |
| - (various arguments)       | None     | Mixed      | Any additional arguments for `tcpreplay`, formatted as key-value pairs. Supported arguments may include speed, duration, and more based on tcpreplay’s options. |

Example `config.yaml`:

```yaml
run_config:
  netmap_mode: true
  speed_check: true
  speed_check_interval: 3
  speed_threshold: 1.2
  is_sudo: true

pcap_files:
  - file: path/to/pcap1.pcap
    percentage: 50
    interface: eth0
  - file: path/to/pcap2.pcap
    percentage: 50
    interface: eth0

tcpreplay_args:
  some_arg: 0
```

### load.yaml

The parameters for `load.yaml` vary based on the selected test type (`max_perf`, `stability`, `spike`, `custom`).

#### max_perf

| Parameter              | Default | Type    | Description                                                                                     |
|------------------------|---------|---------|-------------------------------------------------------------------------------------------------|
| steps                  | 1       | Integer | Number of test steps to execute in a sequence.                                                  |
| impact                 | 0       | Integer | Impact adjustment time (in seconds) added to each step duration.                                |
| base_speed_pps         | None    | Float   | Base packets-per-second speed for this test (set either `base_speed_pps` or `base_speed_mbps`). |
| base_speed_mbps        | None    | Float   | Base megabits-per-second speed for this test.                                                   |
| start_speed_percent    | 0       | Float   | Starting load percentage as a fraction of the base speed.                                       |
| increment_percent      | 0       | Float   | Percentage increment to apply to the load after each step.                                      |
| total_sessions_per_min | None    | Integer | Total number of sessions expected per minute at full load.                                      |

Example `load.yaml` for `max_perf`:

```yaml
max_perf:
  steps: 5
  impact: 10
  base_speed_mbps: 100
  start_speed_percent: 10
  increment_percent: 10
  total_sessions_per_min: 5000
```

#### stability

| Parameter              | Default  | Type    | Description                                                                                     |
|------------------------|----------|---------|-------------------------------------------------------------------------------------------------|
| steps                  | 1        | Integer | Number of test steps for stability check.                                                       |
| impact                 | 0        | Integer | Impact adjustment time (in seconds) added to each step duration.                                |
| base_speed_pps         | None     | Float   | Base packets-per-second speed for this test (set either `base_speed_pps` or `base_speed_mbps`). |
| base_speed_mbps        | None     | Float   | Base megabits-per-second speed for this test.                                                   |
| step_duration          | Required | Integer | Duration (in seconds) for each stability test step.                                             |
| step_percent           | 100.0    | Float   | Load percentage for each stability step.                                                        |
| total_sessions_per_min | None     | Integer | Total number of sessions expected per minute at full load.                                      |

Example `load.yaml` for `stability`:

```yaml
stability:
  steps: 3
  impact: 10
  base_speed_mbps: 100
  step_duration: 60
  step_percent: 100
  total_sessions_per_min: 5000
```

#### spike

| Parameter                | Default  | Type    | Description                                                                                     |
|--------------------------|----------|---------|-------------------------------------------------------------------------------------------------|
| steps                    | 1        | Integer | Number of test steps for spike test.                                                            |
| impact                   | 0        | Integer | Impact adjustment time (in seconds) added to each step duration.                                |
| base_speed_pps           | None     | Float   | Base packets-per-second speed for this test (set either `base_speed_pps` or `base_speed_mbps`). |
| base_speed_mbps          | None     | Float   | Base megabits-per-second speed for this test.                                                   |
| spike_duration           | Required | Integer | Duration (in seconds) for each spike.                                                           |
| stability_speed_duration | Required | Integer | Duration (in seconds) for stability period after each spike.                                    |
| stability_speed_percent  | 100.0    | Float   | Load percentage for the stability period after each spike.                                      |
| spike_base_percent       | Required | Float   | Starting percentage for the spike.                                                              |
| increment_percent        | 0        | Float   | Percentage increment for each spike.                                                            |
| total_sessions_per_min   | None     | Integer | Total number of sessions expected per minute at full load.                                      |
| pcap_for_spike           | None     | List    | Specific PCAP files to use for spikes (by file path).                                           |

Example `load.yaml` for `spike`:

```yaml
spike:
  steps: 3
  impact: 5
  base_speed_mbps: 50
  spike_duration: 10
  stability_speed_duration: 60
  stability_speed_percent: 80
  spike_base_percent: 150
  increment_percent: 10
  total_sessions_per_min: 10000
  pcap_for_spike:
    - path/to/pcap1.pcap
```

#### custom

| Parameter              | Default | Type    | Description                                                                       |
|------------------------|---------|---------|-----------------------------------------------------------------------------------|
| steps                  | 1       | Integer | Number of steps for custom test.                                                  |
| impact                 | 0       | Integer | Impact adjustment time (in seconds) added to each step duration.                  |
| base_speed_pps         | None    | Float   | Base packets-per-second speed (set either `base_speed_pps` or `base_speed_mbps`). |
| base_speed_mbps        | None    | Float   | Base megabits-per-second speed.                                                   |
| total_sessions_per_min | None    | Integer | Total number of sessions per minute at 100% load.                                 |

Example `load.yaml` for `custom`:

```yaml
custom:
  steps: 2
  impact: 10
  base_speed_pps: 100000
  total_sessions_per_min: 8000
```

### Examples

1. Run a maximum performance test with custom configuration:
    ```bash
    python main.py --config custom_config.yaml --load max_perf_load.yaml --test_type max_perf --test_id 1 --test_tag MyTest
    ```

2. Run a stability test with the default configuration files:
    ```bash
    python main.py --test_type stability
    ```
3. Specify a sudo password for privileged operations:
    ```bash
    python main.py --config config.yaml --load load.yaml --test_type spike --sudo_password mypassword
    ```

## Logs and Reports

Logs are saved in the `log` directory with both error and full logs for each test run. Reports, including visual graphs,
are saved in the `load_tests` directory under the specific test folder, structured by test type and ID.

## Visualization

PcapBlaster generates visualizations of test metrics as PNG and HTML files using Plotly, stored in `graphs` within the
test folder.

Generated graphs include:

- Performance over time for each step.
- Cumulative performance across all steps.

PcapBlaster provides an efficient, detailed solution for load testing with PCAP files, allowing for analysis and
visualization of test metrics to optimize network performance.
