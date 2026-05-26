# OWON XDM2041 Controller

This repository contains a Python-based desktop application for controlling and logging data from an OWON XDM2041 digital multimeter and other compatible VISA instruments. It provides a graphical user interface for real-time measurements, data streaming, logging, and exporting.

The application is built using `customtkinter` for the GUI, `pyvisa` for instrument communication, and `matplotlib` for live data plotting. It also includes a supervisor utility that monitors device connectivity and automatically launches the main GUI when the multimeter is detected.

## Features

-   **Graphical User Interface**: An intuitive GUI built with `customtkinter` to control the multimeter.
-   **Instrument Communication**: Connects to devices using `pyvisa`, supporting USB-TMC and serial resources.
-   **Device Profiles**: Supports auto-detection and specific profiles for different instruments, such as the Agilent 34401A.
-   **Measurement Modes**: Perform measurements in various modes, including VDC, VAC, Resistance (OHM), and Capacitance (F).
-   **Data Streaming**: Stream measurements at a user-defined interval with a live-updating display and plot.
-   **Data Logging**: Automatically log all measurements to daily `JSONL` files in the `logs/` directory.
-   **Data Export**: Export logged data to `.txt` and `.csv` formats.
-   **Calibration**: Apply and save custom calibration offsets for each measurement mode.
-   **Averaging**: Enable measurement averaging to improve reading stability.
-   **Simulator Mode**: Includes a built-in simulator for testing and development without physical hardware.

## Installation

### Prerequisites

-   Python 3.10 or newer.
-   A VISA backend is required for `pyvisa` to communicate with the hardware. `pyvisa-py` is included in the requirements and serves as a pure Python backend. Alternatively, you can install NI-VISA.

### Setup

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/ascent-bois/owon-digital-xdm2041.git
    cd owon-digital-xdm2041
    ```

2.  **Install the required Python packages:**
    ```sh
    pip install -r requirements.txt
    ```

### Linux Setup (For USBTMC Devices)

To allow the application to access the USB device without running as root, you need to add a `udev` rule.

1.  Copy the provided `udev` rule to the system directory:
    ```sh
    sudo cp etc/udev/rules.d/99-usbtmc.rules /etc/udev/rules.d/
    ```

2.  Reload the `udev` rules for the changes to take effect:
    ```sh
    sudo udevadm control --reload-rules && sudo udevadm trigger
    ```

3.  You may need to unplug and reconnect the device for the new permissions to apply.

## Usage

### Running the Application

The application consists of a supervisor that monitors for the device and a main GUI. To start the supervisor, run the `src` module from the root of the repository:

```sh
python -m src
```

A small window will appear, indicating whether the multimeter is connected or disconnected. When a compatible device is detected, the main `meter_gui` application will launch automatically.

If the supervisor cannot find the device, you can launch the GUI directly and use the "SIMULATE" resource for testing:
```sh
python -m src.meter_gui
```

### GUI Overview

-   **Resource Selection**: The top-left dropdown lists all detected VISA resources. Select your device from the list or choose `SIMULATE` to run without hardware. Click `Refresh` to scan for devices again.
-   **Profile**: Select an instrument profile or leave it as `Auto-detect`.
-   **Connect**: Click to establish a connection with the selected device.
-   **Measure**: Perform a single measurement using the selected Mode and Range. Buttons for Resistance (Ω) and Capacitance (F) are provided for convenience.
-   **Stream**: Start or stop continuous measurements at the specified interval.
-   **Logging**: Enable the "Log" checkbox to save all measurements to a file.
-   **Export**: Use the `Export TXT` and `Export CSV` buttons to save the contents of the current log file. If "Auto-export on stop" is checked, a CSV report will be generated when streaming is stopped.
-   **Display**: The main display shows the latest measurement value and unit, with a live-updating plot below it.

## Data Logging & Configuration

-   **Logs**: When logging is enabled, all measurement data is appended to a `JSONL` file in the `logs/` directory. A new file is created for each day with the format `measurements_YYYYMMDD.jsonl`. Each line in the file is a JSON object representing a single measurement.

-   **Configuration**: The `calibration.json` file stores application settings, including calibration offsets and averaging preferences. This file is loaded on startup and saved when calibration settings are changed via the GUI.
    ```json
    {
      "calibration": {
        "VDC": 0.0,
        "VAC": 0.0,
        "A": 0.0,
        "OHM": 0.0,
        "HZ": 0.0,
        "CAP": 0.0
      },
      "averaging": {
        "enabled": false,
        "count": 1
      },
      "profile": "generic",
      "custom_cmds": {}
    }
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
