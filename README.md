
# Android Folder Puller (ADB)

A simple Windows GUI tool to pull folders from an Android device using ADB (Android Debug Bridge). The tool automatically downloads the latest ADB platform-tools if not present, checks for a connected device, and provides a user-friendly interface for selecting remote and local folders.

## Features

- **Automatic ADB Download:** Downloads and extracts the latest platform-tools if not found locally.
- **Device Detection:** Checks for a connected Android device and provides instructions if not found.
- **GUI Interface:** Easy-to-use interface built with Tkinter for selecting remote (Android) and local (PC) folders.
- **Progress Bar:** Visual feedback during file transfer.
- **USB Debugging Guidance:** Step-by-step instructions for enabling/disabling USB debugging on your device.

## Requirements

- Windows OS
- Python 3.7+
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

1. Clone this repository:

   ```sh
   git clone https://github.com/JMR-dev/android_file_handler_adb.git
   cd android_file_handler_adb
   ```

2. Install dependencies using Poetry:

   ```sh
   poetry install
   ```

## Usage

1. Activate the virtual environment:

   ```sh
   poetry shell
   ```

   Or manually activate the environment as described in the Poetry documentation.

2. Run the application:

   ```sh
   python android_folder_puller.py
   ```

3. Follow the on-screen instructions:
   - Enter the remote folder path (e.g., `/sdcard/DCIM`)
   - Choose the local destination folder
   - Click **Start Transfer**

## Troubleshooting

- **ADB not found:** The tool will attempt to download and extract ADB automatically.
- **No device detected:** Ensure your device is connected via USB and USB debugging is enabled. The app provides instructions if needed.
- **Permissions:** Some folders on the device may require root access.

## License

MIT License

## Author

[JMR-dev](https://github.com/JMR-dev)
