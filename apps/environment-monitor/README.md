# M5Stack PaperColor 环境监测工作台

这是一个专门面向 **M5Stack PaperColor（C151）** 的本地环境监测项目，在其 400×600 全彩墨水屏上显示温湿度、时间和电源状态。

![M5Stack PaperColor 环境监测界面预览](ui_preview_v5.png)

本目录是一个独立的 PlatformIO 项目。下面的命令默认先从仓库根目录进入本目录：

```bash
cd apps/environment-monitor
```

首次使用时，请先在仓库根目录安装构建工具：

```bash
python3 -m pip install -r requirements.txt
```

## 硬件

- 主控：ESP32-S3R8（16MB Flash、8MB PSRAM）
- 屏幕：4 英寸 E Ink Spectra 6 全彩墨水屏，400×600
- 温湿度：SHT40（I²C `0x44`）
- 实时时钟：RX8130CE（I²C `0x32`）
- 电源管理：M5PM1（I²C `0x6e`）
- 电池：1250mAh 锂电池
- 内部 I²C 实机引脚：SDA GPIO3、SCL GPIO2；固件统一使用 `M5.In_I2C`

## 功能与刷新策略

- 每 15 秒采样一次温度和湿度
- 温度相对上次显示值变化大于 0.5°C，或湿度变化大于 2%，触发一次刷新
- 急刷之间至少间隔 60 秒，避免传感器噪声造成连续闪屏
- 环境稳定时每 5 分钟保底全屏刷新，以更新时间和电源信息
- 显示 RX8130CE 时间、日期、星期和 RTC 状态
- 显示电池百分比、电压、USB/电池供电状态
- 可选 Wi-Fi NTP 对时；NTP 成功后不会再被编译时间覆盖
- RTC 无效或掉电时，用固件编译时间兜底；无 NTP 时按住 BtnA 开机可强制执行
- BtnA/BtnB：立即全屏刷新；BtnC：清屏并关机
- 启动时执行 I²C 扫描，并在 setup 完成后的 20 秒内输出诊断信息

> PaperColor 的 ED2208 屏幕不支持局部刷新。单次全屏刷新实测约 16.7 秒，期间主循环和按键扫描会暂停。

## 界面布局

```text
┌────────────────────────────────┐
│ 标题 / 设备摘要 / 总体状态     │  72px
├───────────────┬────────────────┤
│ TEMPERATURE   │ HUMIDITY       │  200px
├───────────────┼────────────────┤
│ TIME          │ BATTERY        │  200px
├───────────────┴────────────────┤
│ 更新时间 / 舒适度 / 按键提示   │  110px
└────────────────────────────────┘
```

## 配置 Wi-Fi

默认固件不包含 Wi-Fi 凭据，仍可依靠 RTC 和编译时间运行。

```bash
cp src/secrets.example.h src/secrets.h
```

然后只修改本地的 `src/secrets.h`：

```cpp
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASS "your_wifi_password"
```

`src/secrets.h` 已由仓库根目录的 `.gitignore` 排除，不要提交真实凭据。

## 编译、烧录与验证

环境要求：PlatformIO Core 6.x。平台和库版本已在 `platformio.ini` 中锁定。

```bash
# 快速回归检查
python3 -m unittest discover -s tests -v

# 离线渲染并检查 UI 越界/重叠
python3 tools/preview_v3.py /tmp/papercolor-ui.png

# 编译
pio run

# 烧录（按实际串口修改）
pio run -t upload --upload-port /dev/cu.usbmodem21201

# 串口监视
pio device monitor -b 115200
```

最近一次本地完整编译资源占用：RAM 7.1%（23284/327680 bytes），Flash 8.6%（563045/6553600 bytes）。

## 源码结构

```text
src/
├── main.cpp             主程序、时间同步和刷新策略
├── env_ui.h             400×600 UI 渲染
├── sht40_driver.h       SHT40 驱动与 CRC 校验
├── rx8130_rtc.h         RX8130CE 主/备用访问路径
├── m5pm1_power.h        电池和供电状态
└── secrets.example.h    本地 Wi-Fi 配置模板
tests/
└── test_project_audit.py  无硬件快速回归检查
tools/
├── gfxrender.py         M5GFX 字体和画布模拟
├── preview_v3.py        当前 UI 预览与边界检查
└── font_metrics.py      字体尺寸检查
```

## 当前验证边界

回归脚本和 PlatformIO 编译不替代硬件测试。发布固件前仍应在实机上检查：冷启动 NTP、RTC 断电恢复、三个按键、USB 插拔、传感器断开以及至少一次跨日运行。
