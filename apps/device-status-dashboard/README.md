# PaperColor Device Status Dashboard

[中文说明](#中文说明)

An offline-first status dashboard for the M5Stack PaperColor (C151). It is a separate PlatformIO application within this repository, designed to make the device itself observable without a network connection.

## MVP features

- Overview page: battery, USB power, microSD usage, temperature/humidity, RTC, and firmware status.
- Details page: microSD card type and root-file count, peripheral health, free heap, PSRAM, build date, and device identity.
- BtnA refreshes data and rescans the microSD card; BtnB switches pages; BtnC clears the screen and powers off.
- Full-screen EPD refresh is limited to five minutes unless the user requests it, because the PaperColor display takes roughly 15–30 seconds per full update.

## microSD handling

The dashboard uses the official PaperColor SPI mapping: SCK GPIO15, MOSI GPIO13, MISO GPIO14, and CS GPIO47. The display and microSD card share SCK/MOSI, so the first hardware test must verify card mounting and display refresh together. Storage scanning is bounded to the first 512 root entries to avoid a long blocking scan.

## Build

From the repository root:

```bash
python3 -m unittest discover -s apps/device-status-dashboard/tests -v
pio run -d apps/device-status-dashboard
pio run -d apps/device-status-dashboard -t upload --upload-port /dev/cu.usbmodem21201
```

## 中文说明

这是面向 M5Stack PaperColor（C151）的离线优先设备状态看板。第一版显示电源、USB、microSD 使用率、温湿度、RTC 和固件状态；按 BtnB 可进入存储与诊断详情页。

microSD 使用官方引脚映射：SCK GPIO15、MOSI GPIO13、MISO GPIO14、CS GPIO47。它与墨水屏共用 SCK/MOSI，因此首次实机烧录时必须同时验证 SD 挂载和屏幕刷新。SD 根目录扫描最多统计 512 项，避免大量文件导致界面长时间无响应。
