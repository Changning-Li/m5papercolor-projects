# M5Stack PaperColor 项目集

[English](README.md)

本仓库集中管理面向 **M5Stack PaperColor（C151）** 全彩墨水屏设备开发的应用、共用代码和硬件资料。

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
