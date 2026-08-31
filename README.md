# M5Stack PaperColor Projects

[中文文档](README.zh-CN.md)

This repository contains applications, shared code, and hardware notes for the **M5Stack PaperColor (C151)** full-color e-ink device.

Current environment-monitor interface:

![M5Stack PaperColor environment monitor preview](apps/environment-monitor/ui_preview_v5.png)

## Repository layout

```text
m5papercolor-projects/
├── apps/                       Independently buildable and flashable applications
│   └── environment-monitor/    Temperature, humidity, time, and power monitor
├── shared/                     Stable code shared by multiple applications
├── hardware/                   Pinout, component, and hardware-test notes
└── docs/                       Cross-application documentation
```

Every application is a standalone PlatformIO project with its own `platformio.ini`, source code, tests, tools, and README. Add new device applications under `apps/<project-name>/`.

## Setup

Install the Python build tooling:

```bash
python3 -m pip install -r requirements.txt
```

`requirements.txt` provides PlatformIO Core. Exact firmware-library versions are pinned in each application's `platformio.ini`; the included preview and test scripts use only the Python standard library.

## Current application

| Application | Status | Description |
| --- | --- | --- |
| [`environment-monitor`](apps/environment-monitor/) | Builds successfully and has been flashed to hardware | Displays temperature, humidity, RTC time, and power status |

## Common commands

Run these commands from the repository root:

```bash
# Run host-side regression tests
python3 -m unittest discover -s apps/environment-monitor/tests -v

# Build the firmware
pio run -d apps/environment-monitor

# Upload the firmware (change the port when needed)
pio run -d apps/environment-monitor -t upload --upload-port /dev/cu.usbmodem21201

# Render and validate the UI preview
python3 apps/environment-monitor/tools/preview_v3.py /tmp/papercolor-ui.png
```

The root `.gitignore` excludes local `.pio` build caches, Wi-Fi credentials, and temporary files, so they are not uploaded to GitHub.
