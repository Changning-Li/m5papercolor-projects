# PaperColor projects

这个仓库用于集中管理针对 **M5Stack PaperColor（C151）** 全彩墨水屏设备开发的应用、共用代码和硬件资料。

当前已完成的环境监测应用界面：

![M5Stack PaperColor 环境监测界面预览](apps/environment-monitor/ui_preview_v5.png)

## 目录结构

```text
PaperColor/
├── apps/                       可独立编译和烧录的应用
│   └── environment-monitor/    温湿度、时间和电源监测
├── shared/                     多个应用真正共用的代码
├── hardware/                   引脚、器件和硬件测试记录
└── docs/                       跨应用的设计与开发文档
```

每个应用都是一个独立的 PlatformIO 项目，拥有自己的 `platformio.ini`、源码、测试、工具和 README。新增项目时，在 `apps/<project-name>/` 下建立完整项目即可。

## 环境准备

安装 Python 构建工具：

```bash
python3 -m pip install -r requirements.txt
```

`requirements.txt` 只提供 PlatformIO Core；固件库的精确版本由各应用的 `platformio.ini` 锁定。应用附带的预览和测试脚本仅使用 Python 标准库。

## 当前应用

| 应用 | 状态 | 说明 |
| --- | --- | --- |
| [`environment-monitor`](apps/environment-monitor/) | 可编译、已实机烧录 | 显示温湿度、RTC 时间和电源状态 |

## 常用命令

以下命令均从仓库根目录执行：

```bash
# 测试
python3 -m unittest discover -s apps/environment-monitor/tests -v

# 编译
pio run -d apps/environment-monitor

# 烧录
pio run -d apps/environment-monitor -t upload --upload-port /dev/cu.usbmodem21201

# 生成界面预览
python3 apps/environment-monitor/tools/preview_v3.py /tmp/papercolor-ui.png
```

本地的 `.pio` 构建缓存、Wi-Fi 密钥和临时文件由仓库根目录的 `.gitignore` 统一排除，不会上传到 GitHub。
