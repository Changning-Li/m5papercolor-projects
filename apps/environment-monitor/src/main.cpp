// =============================================================
// M5PaperColor 环境监测工作台
// 设备: PaperColor (C151)
// ESP32-S3R8 + 4" 400x600 全彩墨水屏 + SHT40 + RX8130CE + M5PM1
//
// 所有板载芯片都挂在 M5Unified 的内部 I2C 总线上
// (PaperColor 实机: SDA = GPIO3, SCL = GPIO2), 统一走 M5.In_I2C,
// 不再单独 Wire.begin(), 避免两个 I2C 外设抢同一组引脚。
// =============================================================

#include <Arduino.h>
#include <M5Unified.h>
#include <M5GFX.h>
#include <WiFi.h>
#include <time.h>
#include <esp_sleep.h>

#include "sht40_driver.h"
#include "rx8130_rtc.h"
#include "m5pm1_power.h"
#include "env_ui.h"

// 本地 Wi-Fi 配置放在不入库的 src/secrets.h 中；未创建时保持离线可编译。
#if __has_include("secrets.h")
#include "secrets.h"
#endif

// ========== 刷新策略配置 ==========
// 全彩墨水屏单次刷新要 16.7 秒且必定全屏 (Panel_ED2208 驱动不支持局部刷新),
// 频繁刷新既闪又费电, 所以把「采样」和「刷屏」解耦:
//   1) 每 SAMPLE_INTERVAL_MS 读一次传感器, 但不一定刷屏
//   2) 数据变化超过阈值 -> 急刷, 但受 MIN_REFRESH_MS 节流, 防传感器抖动连刷
//   3) 一直没变化 -> 每 REFRESH_INTERVAL_MS 保底刷一次, 顺便把时钟推上去
//
// !! 关键: 时间变化【不能】作为急刷条件 !!
//    分钟每分钟都在变, 一旦把它写进判定, 就等于退回「每分钟刷一次」。
//    时钟的推进交给第 3 条的保底周期负责, 代价是屏上时间最多滞后一个保底周期。
// 急刷节流窗口: 数据变化后最早多久才允许再刷一次 (防传感器抖动连刷)
#define SAMPLE_INTERVAL_MS   15000   // 采样判定周期 15 秒
#define MIN_REFRESH_MS       60000   // 1 分钟
// 保底刷新周期: 环境【没变】时多久必须刷一次 (推时钟 + 防残影)
#define REFRESH_INTERVAL_MS  300000  // 5 分钟 (300 秒)

// 触发急刷的环境变化阈值 (严格大于, 噪声不算)
#define TEMP_DELTA  0.5f    // 温度变化 > 0.5 °C
#define HUMI_DELTA  2.0f    // 湿度变化 > 2.0 %
#define VBUS_PRESENT_MV 4000    // 高于此电压认为插着 USB

// 默认只在 RTC 无效/掉电，或开机按住 BtnA 时使用编译时间兜底。
// 不可默认强制，否则每次重启都会把 RTC 调回固件编译日期，并覆盖 NTP 结果。
#define FORCE_RTC_SYNC  0

// 从「编译完成」到「设备真正跑起来」大约要花的时间(编译+烧录+启动), 对时时会补上
// 实测: pre 脚本取时间戳 -> 编译 -> 烧录 -> 硬复位 -> 跑起来, 约 30 秒
#define BUILD_LAG_SEC   32

// 填上 WiFi 账号后, 启动时会通过 NTP 校准 RTC。
// 凭据建议写入 src/secrets.h；不填时仅在 RTC 无效时用编译时间兜底。
#ifndef WIFI_SSID
#define WIFI_SSID  ""
#endif
#ifndef WIFI_PASS
#define WIFI_PASS  ""
#endif
#ifndef NTP_SERVER
#define NTP_SERVER "pool.ntp.org"
#endif
#ifndef TZ_OFFSET
#define TZ_OFFSET  (8 * 3600)      // 东八区
#endif

// ========== 全局对象 ==========
SHT40Sensor sht40;
RX8130RTC   rtc;
M5PM1Power  pm1;
EnvMonitorUI ui;
M5GFX      &display = M5.Display;

unsigned long lastSample = 0;   // 上次采样判定的时刻
unsigned long lastPaint  = 0;   // 上次真正刷屏的时刻
unsigned long startupReportStart = 0; // setup 完成后诊断窗口的起点
bool refreshing = false;        // 刷新忙锁, 防止重入

// 上一次真正刷上屏的数据快照, 用来判断“这次有没有必要刷”
static EnvData  g_shown;
static bool     g_shownValid = false;

// ========== I2C 扫描 (调试用) ==========
void scanI2C() {
    Serial.printf("Internal I2C: SDA=%d SCL=%d\n",
                  M5.In_I2C.getSDA(), M5.In_I2C.getSCL());
    Serial.print("Scan:");
    int found = 0;
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        if (M5.In_I2C.scanID(addr, 100000)) {
            Serial.printf(" 0x%02X", addr);
            found++;
        }
    }
    Serial.printf("  (%d device(s))\n", found);
}

// ========== 采集环境数据 ==========
EnvData collectData() {
    EnvData data;

    data.sensorOK = sht40.read(data.temperature, data.humidity);
    if (!data.sensorOK) {
        data.temperature = 0;
        data.humidity    = 0;
    }

    data.rtcOK = rtc.getDateTime(data.year, data.month, data.day,
                                 data.hour, data.minute, data.second, data.weekday);
    if (!data.rtcOK) {
        data.year = 2000; data.month = 1; data.day = 1;
        data.hour = 0; data.minute = 0; data.second = 0; data.weekday = 0;
    }

    data.powerOK    = pm1.begin();
    data.batteryMV  = pm1.getBatteryVoltage();
    data.batteryPct = pm1.getBatteryPercent();
    data.vbusMV     = pm1.getVBUSVoltage();
    data.chargeState = pm1.getChargeState();

    return data;
}

// ========== 星期推算 (0=周日) ==========
int weekdayFromDate(int y, int m, int d) {
    static const int t[] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
    if (m < 3) y--;
    return (y + y / 4 - y / 100 + y / 400 + t[m - 1] + d) % 7;
}

// ========== 用固件编译时间初始化 RTC ==========
// 上传固件的时间点就是"现在", 因此足够让时钟走起来, 之后联网还能用 NTP 精确校准。
// 优先用 build_time.py 注入的 Unix 时间戳 (绝对时间, 不受编译主机时区影响);
// 没有注入时回退到 __DATE__ / __TIME__ 字符串。
#ifndef BUILD_UNIX_TIME
#define BUILD_UNIX_TIME 0
#endif

bool setRTCFromBuildTime() {
    if (BUILD_UNIX_TIME > 1600000000) {
        // epoch 是 UTC, 加上时区偏移后用 gmtime 得到本地挂钟时间 (不依赖设备 TZ 设置)
        // 再补上编译->烧录->启动这段时间的延迟
        time_t t = (time_t)BUILD_UNIX_TIME + TZ_OFFSET + BUILD_LAG_SEC;
        struct tm ti;
        gmtime_r(&t, &ti);
        bool ok = rtc.setDateTime(ti);
        Serial.printf("RTC set from build time: %04d-%02d-%02d %02d:%02d:%02d (wd=%d)\n",
                      ti.tm_year + 1900, ti.tm_mon + 1, ti.tm_mday,
                      ti.tm_hour, ti.tm_min, ti.tm_sec, ti.tm_wday);
        return ok;
    }

    // 回退: __DATE__ = "Aug 29 2026", __TIME__ = "08:06:11"
    const char *months = "JanFebMarAprMayJunJulAugSepOctNovDec";
    char mon[4] = {0};
    int day = 0, year = 0, hh = 0, mm = 0, ss = 0;
    if (sscanf(__DATE__, "%3s %d %d", mon, &day, &year) != 3) return false;
    if (sscanf(__TIME__, "%d:%d:%d", &hh, &mm, &ss) != 3) return false;

    const char *p = strstr(months, mon);
    if (!p) return false;
    int month = (int)((p - months) / 3) + 1;

    int wd = weekdayFromDate(year, month, day);
    bool ok = rtc.setDateTime(year, month, day, hh, mm, ss, wd);
    Serial.printf("RTC set from build time: %04d-%02d-%02d %02d:%02d:%02d (wd=%d)\n",
                  year, month, day, hh, mm, ss, wd);
    return ok;
}

// ========== NTP 时间同步 ==========
bool tryNTPSync() {
    if (strlen(WIFI_SSID) == 0) {
        Serial.println("WiFi not configured, skip NTP");
        return false;
    }

    Serial.println("WiFi connecting for NTP...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    bool synced = false;
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nSyncing NTP...");
        configTime(TZ_OFFSET, 0, NTP_SERVER);
        struct tm timeinfo;
        if (getLocalTime(&timeinfo, 10000)) {
            Serial.printf("NTP: %04d-%02d-%02d %02d:%02d:%02d\n",
                          timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                          timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
            synced = rtc.setDateTime(timeinfo);
            Serial.println(synced ? "RTC updated from NTP" : "RTC NTP write failed");
        } else {
            Serial.println("NTP response timeout, keep existing RTC");
        }
    } else {
        Serial.println("WiFi failed, skip NTP");
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    return synced;
}

// ========== 确保 RTC 处于可用状态 ==========
// force=true 时用编译时间校准（开机按住 BtnA，或显式把 FORCE_RTC_SYNC 改成 1）。
void ensureRTCTime(bool force) {
    int y, mo, d, h, mi, s, wd;
    bool ok = rtc.getDateTime(y, mo, d, h, mi, s, wd);
    bool vlf = rtc.isVoltageLow();

    Serial.printf("RTC: %s  VLF=%d  driver=%s\n",
                  ok ? rtc.getFormattedTime().c_str() : "read failed",
                  (int)vlf, rtc.usingM5Driver() ? "M5.Rtc" : "raw");

#if FORCE_RTC_SYNC
    force = true;
#endif
    bool needSet = !ok || vlf || y < 2024 || y > 2090;
    if (force || needSet) {
        Serial.printf("RTC sync (%s)\n",
                      force ? "forced by BtnA / build option" : "not initialized");
        setRTCFromBuildTime();

        // 写完后立刻回读校验: 若时间没写进去, 换成「直接寄存器」路径再写一次
        if (!rtc.getDateTime(y, mo, d, h, mi, s, wd) || y < 2024 || y > 2090) {
            Serial.println("WARN: RTC write did not stick -> retry via raw register path");
            rtc.setForceRaw(true);
            rtc.begin();
            setRTCFromBuildTime();
            if (rtc.getDateTime(y, mo, d, h, mi, s, wd)) {
                Serial.printf("RTC (raw retry): %04d-%02d-%02d %02d:%02d:%02d\n",
                              y, mo, d, h, mi, s);
            } else {
                Serial.println("RTC: raw retry also failed");
            }
        } else {
            Serial.printf("RTC verify OK: %04d-%02d-%02d %02d:%02d:%02d\n", y, mo, d, h, mi, s);
        }
    }
}

// ========== 格式化更新时间 ==========
String getUpdateTimestamp() {
    int y, mo, d, h, mi, s, wd;
    if (rtc.getDateTime(y, mo, d, h, mi, s, wd)) {
        char buf[20];
        snprintf(buf, sizeof(buf), "%02d:%02d:%02d", h, mi, s);
        return String(buf);
    }
    return "--:--:--";
}

// ========== 脏数据判定: 这次值不值得刷一次屏? ==========
// 返回 true 才真正刷屏。force=true 时不判定, 直接刷。
//
// !! 关键: 只有「温湿度变化」和「设备状态翻转」才算环境变化 !!
//   - 电量百分比 / 充放电状态 / VBUS 等次要信息【不】进入急刷判定
//     (它们在 100% 满电附近会轻微抖动, 写进判定就退回 60s 闪一次)
//   - 它们的更新交给 REFRESH_INTERVAL_MS 的保底周期, 5 分钟一次
//   - 时间 (时/分/秒) 【故意不判定】: 分钟每分钟都在变, 判了就等于每分钟刷一次。
//     时钟推进由保底周期负责, 屏上时间最多滞后一个保底周期 (5 分钟)。
bool needsRepaint(const EnvData &n) {
    if (!g_shownValid) return true;                                  // 首帧必刷

    unsigned long since = millis() - lastPaint;
    if (since >= REFRESH_INTERVAL_MS) return true;                   // 保底到点必刷
    if (since <  MIN_REFRESH_MS)      return false;                  // 节流窗口内不刷

    const EnvData &o = g_shown;

    // 设备在线状态翻转 (掉线/恢复) 必须刷
    if (n.sensorOK != o.sensorOK) return true;
    if (n.rtcOK    != o.rtcOK   ) return true;

    // 温湿度【严格大于】阈值才算环境变化 (噪声不算)
    if (n.sensorOK) {
        if (fabsf(n.temperature - o.temperature) > TEMP_DELTA) return true;
        if (fabsf(n.humidity    - o.humidity   ) > HUMI_DELTA) return true;
    }

    return false;
}

// ========== 刷新屏幕 ==========
// force=true 无条件刷 (首帧 / 按键 / 常规周期到)
void refreshDisplay(bool force = false) {
    if (refreshing) {
        Serial.println("Already refreshing, skip");
        return;
    }
    refreshing = true;

    EnvData data = collectData();

    if (!force && !needsRepaint(data)) {
        unsigned long since = millis() - lastPaint;
        Serial.printf("[skip] 无实质变化 T=%.1f(%.1f) H=%.1f(%.1f) Bat=%d%%(%d%%) "
                      "| 距上次刷屏 %lus, 距保底刷屏 %lus\n",
                      data.temperature, g_shown.temperature,
                      data.humidity,    g_shown.humidity,
                      data.batteryPct,  g_shown.batteryPct,
                      since / 1000,
                      (REFRESH_INTERVAL_MS > since ? REFRESH_INTERVAL_MS - since : 0) / 1000);
        refreshing = false;
        return;
    }

    // --- 渲染前把「真正交给 UI 的值」打出来, 便于定位屏幕显示异常 ---
    Serial.printf("[render] %s time=%02d:%02d:%02d date=%04d-%02d-%02d wd=%d | "
                  "T=%.1f H=%.1f | Bat=%d%% %dmV vbus=%dmV | "
                  "ok(sht=%d,rtc=%d,pm=%d) upd=%s\n",
                  force ? "force" : "dirty",
                  data.hour, data.minute, data.second,
                  data.year, data.month, data.day, data.weekday,
                  data.temperature, data.humidity,
                  data.batteryPct, data.batteryMV, data.vbusMV,
                  (int)data.sensorOK, (int)data.rtcOK, (int)data.powerOK,
                  getUpdateTimestamp().c_str());

    ui.render(data, getUpdateTimestamp());

    Serial.println("E-Ink refresh...");
    unsigned long t0 = millis();
    display.display();
    Serial.printf("Done. (%lums)\n", (unsigned long)(millis() - t0));

    g_shown      = data;              // 记下这次刷上屏的快照
    g_shownValid = true;
    lastPaint    = millis();

    refreshing = false;
}

// ========== Setup ==========
void setup() {
    auto cfg = M5.config();
    cfg.serial_baudrate = 115200;
    M5.begin(cfg);

    Serial.println("\n=================================");
    Serial.println("M5PaperColor Environment Monitor");
    Serial.println("=================================");
    Serial.printf("Board: %d, Display: %dx%d, EPD: %d\n",
                  (int)M5.getBoard(), display.width(), display.height(),
                  (int)display.isEPD());
    Serial.printf("Build: %s %s (epoch=%lu)\n", __DATE__, __TIME__, (unsigned long)BUILD_UNIX_TIME);

    // 关闭自动显示, 只在需要时手动刷新
    display.setAutoDisplay(false);

    // 墨水屏掉电后仍保留上一帧: 开机先清一次白屏, 避免把旧画面误当成当前数据
    display.fillScreen(UI_BG);
    display.display();

    delay(50);
    scanI2C();

    bool pmOK = pm1.begin();
    bool rtcOK = rtc.begin();
    bool shtOK = sht40.begin();

    Serial.printf("M5PM1: %s\n", pmOK ? "OK" : "FAIL");
    Serial.printf("RX8130CE: %s\n", rtcOK ? "OK" : "FAIL");
    Serial.printf("SHT40: %s\n", shtOK ? "OK" : "FAIL");

    if (shtOK) {
        uint32_t sn = 0;
        if (sht40.readSerial(sn)) Serial.printf("SHT40 S/N: 0x%08X\n", (unsigned)sn);
    }

    // 先读取启动按键，再尝试 NTP。NTP 成功后绝不再用编译时间覆盖它。
    M5.update();
    bool forceSync = M5.BtnA.isPressed();
    bool ntpSynced = tryNTPSync();
    if (!ntpSynced) {
        ensureRTCTime(forceSync);
    } else {
        Serial.println("RTC verified by NTP; build-time fallback skipped");
    }
    Serial.println("Tip: without NTP, hold BtnA while booting to use build time");

    ui.begin(&display);

    Serial.println("First refresh...");
    refreshDisplay(true);          // 首帧无条件刷
    lastSample = lastPaint = millis();
    startupReportStart = millis(); // 两次 EPD 刷新结束后才开始 20 秒诊断窗口

    Serial.printf("刷新策略: 采样 %lus / 急刷节流 %lus / 保底 %lus / "
                  "温度阈值 >%.1f°C / 湿度阈值 >%.1f%% (电量/USB 不参与急刷)\n",
                  (unsigned long)(SAMPLE_INTERVAL_MS / 1000),
                  (unsigned long)(MIN_REFRESH_MS / 1000),
                  (unsigned long)(REFRESH_INTERVAL_MS / 1000),
                  TEMP_DELTA, HUMI_DELTA);

    Serial.println("Setup complete.\n");
}

// ========== 开机诊断: 前 20 秒每 3 秒打印一次状态, 方便抓串口日志 ==========
void startupReport() {
    static unsigned long last = 0;
    unsigned long now = millis();
    if (startupReportStart == 0 || now - startupReportStart > 20000) return;
    if (now - last < 3000) return;
    last = now;

    EnvData data = collectData();
    Serial.printf("[boot] build=%s %s | rtc=%s | T=%.1f H=%.1f | bat=%d%%/%dmV vbus=%dmV\n",
                  __DATE__, __TIME__, rtc.getFormattedTime().c_str(),
                  data.temperature, data.humidity,
                  data.batteryPct, data.batteryMV, data.vbusMV);
}

// ========== Main Loop ==========
void loop() {
    M5.update();   // 维护 M5Unified 内部状态 (按键扫描等)

    startupReport();

    unsigned long now = millis();

    // 按键 A/B: 无条件强制刷新
    if (M5.BtnA.wasPressed() || M5.BtnB.wasPressed()) {
        Serial.println("Btn A/B: force refresh");
        refreshDisplay(true);
        lastSample = millis();
        delay(50);
        return;
    }

    if (M5.BtnC.wasPressed()) {
        Serial.println("Btn C: power off");
        display.fillScreen(UI_BG);
        display.display();
        delay(200);
        M5.Power.powerOff();
        esp_deep_sleep_start();   // 兜底
    }

    // 常规周期到 -> 无条件刷一次 (保证时钟持续推进)
    if (now - lastPaint >= REFRESH_INTERVAL_MS) {
        refreshDisplay(true);
        lastSample = millis();
    }
    // 采样周期到 -> 做脏数据判定, 变了才刷
    else if (now - lastSample >= SAMPLE_INTERVAL_MS) {
        refreshDisplay(false);
        lastSample = millis();
    }

    delay(50);
}
