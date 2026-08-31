# M5Stack PaperColor 项目集

[English](README.md)

本仓库集中管理面向 **M5Stack PaperColor（C151）** 全彩墨水屏设备开发的应用、共用代码和硬件资料。

![M5Stack PaperColor 设备概览](docs/images/m5stack-papercolor-overview.png)

## 关于 M5Stack PaperColor

PaperColor（SKU：C151）是一款基于乐鑫 **ESP32-S3R8** 的便携式全彩墨水屏开发设备。它配备 4 英寸 400×600 Spectra 6 屏幕，适合低功耗信息展示；板载传感器、RTC、microSD 卡槽、音频硬件和扩展接口，也使它适合嵌入式应用开发。

| 硬件 | 规格 |
| --- | --- |
| 主控 | ESP32-S3R8，Xtensa LX7 双核，最高 240 MHz |
| 存储 | 16 MB Flash、8 MB Octal PSRAM |
| 屏幕 | 4 英寸 ED2208 E Ink Spectra 6 全彩墨水屏，400×600 |
| 连接 | 2.4 GHz Wi-Fi、USB-C 供电和数据接口 |
| 扩展存储 | microSD 卡槽 |
| 板载器件 | SHT40 温湿度传感器、RX8130CE RTC、M5PM1 电源管理 |
| 交互与扩展 | 3 个用户按键、1 个电源键、红外发射、2 个 RGB LED、HY2.0-4P 扩展接口 |
| 音频 | ES8311 音频编解码器、MEMS 麦克风、1 W 扬声器 |
| 电源 | 1250 mAh 电池 |

完整规格、管脚映射、原理图和硬件注意事项请参阅 [M5Stack PaperColor 官方文档](https://docs.m5stack.com/zh_CN/core/PaperColor)。全屏刷新时间会随画面复杂度变化，约为 15–30 秒；因此应用应按需刷新，而不是持续刷新。

当前环境监测应用的界面：

![M5Stack PaperColor 环境监测界面预览](apps/environment-monitor/ui_preview_v5.png)

## 仓库结构

```text
m5papercolor-projects/
├── apps/                       可独立编译和烧录的应用
│   └── environment-monitor/    温湿度、时间和电源监测
├── shared/                     多个应用真正共用的稳定代码
├── hardware/                   引脚、器件和硬件测试记录
└── docs/                       跨应用的开发文档
```

每个应用都是独立的 PlatformIO 项目，拥有自己的 `platformio.ini`、源码、测试、工具和 README。未来新增应用时，在 `apps/<project-name>/` 下建立完整项目即可。

## 环境准备

安装 Python 构建工具：

```bash
python3 -m pip install -r requirements.txt
```

`requirements.txt` 提供 PlatformIO Core；固件库的精确版本由各应用的 `platformio.ini` 锁定。随项目附带的预览和测试脚本仅使用 Python 标准库。

## 当前应用

| 应用 | 状态 | 说明 |
| --- | --- | --- |
| [`environment-monitor`](apps/environment-monitor/) | 已通过编译并烧录到实机 | 显示温湿度、RTC 时间和电源状态 |

## 常用命令

以下命令均从仓库根目录执行：

```bash
# 运行主机端回归测试
python3 -m unittest discover -s apps/environment-monitor/tests -v

# 编译固件
pio run -d apps/environment-monitor

# 烧录固件（按需要修改串口）
pio run -d apps/environment-monitor -t upload --upload-port /dev/cu.usbmodem21201

# 离线渲染并检查界面预览
python3 apps/environment-monitor/tools/preview_v3.py /tmp/papercolor-ui.png
```

仓库根目录的 `.gitignore` 会排除本地 `.pio` 构建缓存、Wi-Fi 凭据和临时文件，因此它们不会上传到 GitHub。
