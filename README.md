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
    - `scapy`
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

| Field          | Description                                                                           |
|----------------|---------------------------------------------------------------------------------------|
| run_config     | General run configuration, such as netmap mode, speed check interval, and thresholds. |
| pcap_files     | List of PCAP files to be used in the test, including load percentages and interfaces. |
| tcpreplay_args | Additional arguments for tcpreplay.                                                   |

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

#### load.yaml

The `load.yaml` file specifies the load configuration parameters for the test type chosen (`max_perf`, `stability`,
`spike`, or `custom`). Each test type has unique fields.

Example `load.yaml` for `max_perf` test:

```yaml
max_perf:
  steps: 3
  step_duration: 30
  impact: 10
  base_speed_mbps: 1
  start_speed_percent: 100
  increment_percent: 20
  total_sessions_per_min: 1000

stability:
  step_duration: 3600
  impact: 10
  base_speed_pps: 10000
  step_percent: 80
  total_sessions_per_min: 10000

spike:
  steps: 3
  spike_duration: 60
  stability_speed_duration: 300
  impact: 10
  base_speed_pps: 10000
  stability_speed_percent: 70
  spike_base_percent: 90
  increment_percent: 5
  total_sessions_per_min: 10000
  pcap_for_spike:
    - path/to/pcap1.pcap
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
