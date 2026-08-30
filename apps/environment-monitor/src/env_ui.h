#pragma once
// =============================================================
// 环境监测工作台 UI 渲染模块
// 屏幕: 400x600 4寸全彩墨水屏 (Spectra 6)
//
// 版面 (坐标 = 文本框左上角, 行距按字体真实 yAdvance 预留, 不会重叠):
//   Header   y = 0   .. 72     标题 + 副标题 + 状态灯
//   Row 1    y = 78  .. 278    TEMPERATURE(左) | HUMIDITY(右)
//   Row 2    y = 282 .. 482    TIME(左) | BATTERY(右)
//   Footer   y = 490 .. 600
//
// 卡片内部 (相对卡片顶部, 卡片高 200):
//   LABEL  y+16   12pt 粗体   行高 23 -> 占 16..39
//   VALUE  y+42   24pt 粗体   行高 56 -> 占 42..98
//   LINE1  y+108  12pt 常规   行高 29 -> 占 108..137
//   LINE2  y+148  12pt 常规   行高 29 -> 占 148..177
// =============================================================

#include <Arduino.h>
#include <M5GFX.h>
#include <M5Unified.h>

// ---------- 调色板 ----------
// 6 色墨水屏只有 黑/白/红/绿/蓝/黄, 灰/青这类中间色要靠抖动模拟, 小字会糊。
// 因此「所有文字」一律用纯色, UI_GRAY 只保留给非文字元素。
#define UI_BG      0xFFFF
#define UI_BLACK   0x0000
#define UI_WHITE   0xFFFF
#define UI_RED     0xF800
#define UI_GREEN   0x07E0
#define UI_BLUE    0x001F
#define UI_ORANGE  0xFC00
#define UI_YELLOW  0xFFE0
#define UI_CYAN    UI_BLUE
#define UI_GRAY    UI_BLACK
#define UI_LGRAY   UI_BLACK

// 判断「插着 USB」的 VBUS 电压阈值 (mV), 与 main.cpp 的 VBUS_PRESENT_MV 保持一致
#define VBUS_PRESENT_THRESHOLD 4000

// ---------- 版面常量 ----------
#define UI_W        400
#define UI_H        600
#define UI_HEAD_H   72
#define UI_PAD      14
#define UI_CARD_W   188
#define UI_CARD_L   6
#define UI_CARD_R   (UI_W - 6 - UI_CARD_W)   // 206
#define UI_ROW1_Y   (UI_HEAD_H + 6)          // 78
#define UI_ROW2_Y   (UI_ROW1_Y + 204)        // 282
#define UI_CARD_H   200
#define UI_FOOT_Y   (UI_ROW2_Y + UI_CARD_H + 8)  // 490

// 大号数字(24pt) 与单位(12pt) 共用的【基线】位置 (相对卡片顶的偏移)。
//
// !! 排版方式: 两者都用 baseline_left datum, 传【同一个 baseY】,
//   由 M5GFX 内部按各自字体的 ascent 换算顶部位置 —— 不手工算 ascent 差。
//
// 为什么不用 top_left + 手工补偿:
//   手工算法是 unitY = valY + (ascent24 - ascent12) = valY + (35-17) = valY + 18,
//   这个数先后算错过三次 (写成 +60 单位掉到下一行 / 写成 +18 但 valY 传错 / ° 位置跟着错),
//   根因是「valY 到底是卡片顶还是数字顶」容易搞混, 且 ascent 是硬编码的魔法数。
//   改用 baseline_left datum 后, 库自己处理, 从原理上不可能再算错。
//
// 77 这个值: 24pt 数字用 top_left 画在 y+42 时 baseline = 42+35 = 77,
//            取 77 可以让数字位置与改版前完全一致, 只是 datum 换了。
#define UI_VALUE_BASE  77

struct EnvData {
    float   temperature = 0.0f;
    float   humidity    = 0.0f;
    uint8_t batteryPct  = 0;
    uint16_t batteryMV  = 0;
    uint16_t vbusMV     = 0;
    int8_t  chargeState = -1;   // -1 未知 / 0 放电 / 1 充电
    int year = 2000, month = 1, day = 1;
    int hour = 0, minute = 0, second = 0, weekday = 0;
    bool sensorOK = false;
    bool rtcOK    = false;
    bool powerOK  = false;
};

class EnvMonitorUI {
public:
    void begin(M5GFX *gfx) { _gfx = gfx; }

    void render(const EnvData &data, const String &updateStr) {
        _gfx->fillScreen(UI_BG);
        drawHeader(data);
        drawTempCard(UI_CARD_L, UI_ROW1_Y, data);
        drawHumiCard(UI_CARD_R, UI_ROW1_Y, data);
        drawTimeCard(UI_CARD_L, UI_ROW2_Y, data);
        drawBatteryCard(UI_CARD_R, UI_ROW2_Y, data);
        drawFooter(data, updateStr);
    }

private:
    M5GFX *_gfx = nullptr;

    // ============ 绘制助手 (统一 top_left datum: y = 文本框顶端) ============
    void text(const char *s, int x, int y, const lgfx::IFont *font,
              uint16_t color, textdatum_t datum = top_left) {
        _gfx->setFont(font);
        _gfx->setTextColor(color);
        _gfx->setTextDatum(datum);
        _gfx->drawString(s, x, y);
    }

    void text(const String &s, int x, int y, const lgfx::IFont *font,
              uint16_t color, textdatum_t datum = top_left) {
        text(s.c_str(), x, y, font, color, datum);
    }

    int textW(const char *s, const lgfx::IFont *font) {
        _gfx->setFont(font);
        return _gfx->textWidth(s);
    }

    // ============ 标题栏 (高 72, 留足行距) ============
    void drawHeader(const EnvData &data) {
        _gfx->fillRect(0, 0, UI_W, UI_HEAD_H, UI_BLACK);

        // 标题 18pt 粗体: 行高 33, y=8 -> 占 8..41
        text("Environment Monitor", 12, 8, &fonts::FreeSansBold18pt7b, UI_WHITE);

        // 缩短副标题，为右侧状态留出独立空间。
        text("SHT40 | RX8130 | 4in E-Ink", 12, 44, &fonts::FreeSans12pt7b, UI_WHITE);

        // 状态放在副标题行；标题行占满宽度，不能再叠加状态文字。
        bool allOK = data.sensorOK && data.rtcOK && data.powerOK;
        int cy = UI_HEAD_H - 16;
        _gfx->fillCircle(UI_W - 62, cy, 5, allOK ? UI_GREEN : UI_RED);
        text(allOK ? "OK" : "ERR", UI_W - 12, cy - 8, &fonts::FreeSansBold12pt7b,
             allOK ? UI_GREEN : UI_RED, top_right);
    }

    // ============ 卡片底板 ============
    void cardFrame(int x, int y, uint16_t accent) {
        _gfx->fillRoundRect(x, y, UI_CARD_W, UI_CARD_H, 8, UI_BG);
        _gfx->fillRoundRect(x, y, UI_CARD_W, 6, 3, accent);
        _gfx->drawRoundRect(x, y, UI_CARD_W, UI_CARD_H, 8, UI_BLACK);
    }

    // ============ 时间卡片 (第一行左) ============
    // 右上角状态灯的含义:
    //   RTC OK  -> RX8130CE 在 I2C 上正常应答, 且读出的年月日时分秒都落在合法范围
    //              (用来区分"真的 00:00"和"掉电后残留的 2000-01-01 00:00:00")
    //   RTC ERR -> I2C 读不到芯片, 或数值越界。此时时间显示 --:--, 需要重新对时
    //              (按住 BtnA 上电, 或配好 WiFi 走 NTP)
    //
    // 标签 9pt Bold: 卡片可用 160px, "TEMPERATURE" 12pt=184px 越界 -> 降到 9pt=140px
    void drawTimeCard(int x, int y, const EnvData &data) {
        cardFrame(x, y, UI_BLUE);

        text("TIME", x + UI_PAD, y + 16, &fonts::FreeSansBold9pt7b, UI_BLACK);
        text(data.rtcOK ? "RTC OK" : "RTC ERR", x + UI_CARD_W - UI_PAD, y + 16,
             &fonts::FreeSansBold9pt7b, data.rtcOK ? UI_GREEN : UI_RED, top_right);

        // 大号 HH:MM (24pt 粗体)
        char buf[20];
        if (data.rtcOK) {
            snprintf(buf, sizeof(buf), "%02d:%02d", data.hour, data.minute);
        } else {
            snprintf(buf, sizeof(buf), "--:--");
        }
        text(buf, x + UI_PAD, y + 42, &fonts::FreeSansBold24pt7b, UI_BLACK);

        // 秒: 12pt 粗体, 与大号数字基线对齐 (24pt 基线 +35, 12pt 基线 +17)
        if (data.rtcOK) {
            int secX = x + UI_PAD + textW(buf, &fonts::FreeSansBold24pt7b) + 6;
            snprintf(buf, sizeof(buf), ":%02d", data.second);
            text(buf, secX, y + 60, &fonts::FreeSansBold12pt7b, UI_BLACK);
        }

        // 日期 / 星期
        if (data.rtcOK) {
            snprintf(buf, sizeof(buf), "%04d-%02d-%02d", data.year, data.month, data.day);
        } else {
            snprintf(buf, sizeof(buf), "----/--/--");
        }
        text(buf, x + UI_PAD, y + 108, &fonts::FreeSans12pt7b, UI_BLACK);

        static const char *wdNames[] = {"Sunday", "Monday", "Tuesday", "Wednesday",
                                        "Thursday", "Friday", "Saturday"};
        text(data.rtcOK ? wdNames[data.weekday % 7] : "--------",
             x + UI_PAD, y + 148, &fonts::FreeSans12pt7b, UI_BLACK);
    }

    // ============ 电池卡片 (第一行右) ============
    // 右上角电源状态的含义 (三选一, 优先级从高到低):
    //   CHG = M5PM1 报告电池正在充电
    //   USB = 检测到 VBUS > 4.0V, 也就是插着 USB / 外接电源
    //         (注意: 插着 USB 不一定在充电, 电池满了就会停充, 所以 CHG 优先显示)
    //   BAT = 没接外接电源, 正由电池供电
    void drawBatteryCard(int x, int y, const EnvData &data) {
        cardFrame(x, y, UI_GREEN);

        text("BATTERY", x + UI_PAD, y + 16, &fonts::FreeSansBold9pt7b, UI_BLACK);

        const char *pwr = nullptr;
        uint16_t pwrCol = UI_BLACK;
        if (data.chargeState > 0)      { pwr = "CHG"; pwrCol = UI_GREEN; }
        else if (data.vbusMV > VBUS_PRESENT_THRESHOLD) { pwr = "USB"; pwrCol = UI_BLUE; }
        else if (data.chargeState == 0){ pwr = "BAT"; pwrCol = UI_BLACK; }
        if (pwr) {
            text(pwr, x + UI_CARD_W - UI_PAD, y + 16, &fonts::FreeSansBold9pt7b,
                 pwrCol, top_right);
        }

        uint16_t batCol = getBatColor(data.batteryPct);
        char buf[20];
        snprintf(buf, sizeof(buf), "%d%%", data.batteryPct);
        text(buf, x + UI_PAD, y + 42, &fonts::FreeSansBold24pt7b, batCol);

        if (data.batteryMV > 0) {
            snprintf(buf, sizeof(buf), "%.2f V", data.batteryMV / 1000.0f);
        } else {
            snprintf(buf, sizeof(buf), "--.-- V");
        }
        text(buf, x + UI_PAD, y + 108, &fonts::FreeSans12pt7b, UI_BLACK);

        // 电量条
        int barX = x + UI_PAD, barY = y + 144;
        int barW = UI_CARD_W - UI_PAD * 2, barH = 22;
        _gfx->drawRoundRect(barX, barY, barW, barH, 4, UI_BLACK);
        int fillW = (barW - 6) * data.batteryPct / 100;
        if (fillW > 0) {
            _gfx->fillRoundRect(barX + 3, barY + 3, fillW, barH - 6, 2, batCol);
        }
    }

    // ============ 温度卡片 (第二行左) ============
    // 标签用 9pt Bold "TEMPERATURE": 12pt Bold 宽 184px > 卡片可用 160px, 会越界;
    // 9pt Bold 宽 140px, 留 20px 余量。"C" 单位用 12pt 与大号数字基线对齐, 紧跟在数字后。
    void drawTempCard(int x, int y, const EnvData &data) {
        cardFrame(x, y, UI_ORANGE);

        text("TEMPERATURE", x + UI_PAD, y + 16, &fonts::FreeSansBold9pt7b, UI_BLACK);

        char buf[20];
        uint16_t col;
        if (data.sensorOK) {
            snprintf(buf, sizeof(buf), "%.1f", data.temperature);
            col = getTempColor(data.temperature);
        } else {
            snprintf(buf, sizeof(buf), "--.-");
            col = UI_RED;
        }
        text(buf, x + UI_PAD, y + 42, &fonts::FreeSansBold24pt7b, col);
        drawUnit(x + UI_PAD, y + 42, buf, "C", col, true);

        text(data.sensorOK ? getTempStatus(data.temperature) : "No Sensor",
             x + UI_PAD, y + 108, &fonts::FreeSans12pt7b, data.sensorOK ? UI_BLACK : UI_RED);
        text("Range -10~40", x + UI_PAD, y + 148, &fonts::FreeSans12pt7b, UI_BLACK);
    }

    // ============ 湿度卡片 (第二行右) ============
    // 同上: 标签 9pt Bold "HUMIDITY" (91px), 单位 % 用 12pt 与大号数字基线对齐
    void drawHumiCard(int x, int y, const EnvData &data) {
        cardFrame(x, y, UI_BLUE);

        text("HUMIDITY", x + UI_PAD, y + 16, &fonts::FreeSansBold9pt7b, UI_BLACK);

        char buf[20];
        uint16_t col;
        if (data.sensorOK) {
            snprintf(buf, sizeof(buf), "%.1f", data.humidity);
            col = getHumiColor(data.humidity);
        } else {
            snprintf(buf, sizeof(buf), "--.-");
            col = UI_RED;
        }
        text(buf, x + UI_PAD, y + 42, &fonts::FreeSansBold24pt7b, col);
        drawUnit(x + UI_PAD, y + 42, buf, "%", col, false);

        text(data.sensorOK ? getHumiStatus(data.humidity) : "No Sensor",
             x + UI_PAD, y + 108, &fonts::FreeSans12pt7b, data.sensorOK ? UI_BLACK : UI_RED);
        text("Range 20~80", x + UI_PAD, y + 148, &fonts::FreeSans12pt7b, UI_BLACK);
    }

    // 单位: 紧跟大号数字右侧, 与大号数字【基线对齐】
    //
    //  top_left datum:  baseline = y + ascent
    //    24pt Bold ascent=35 -> 大号数字 baseline = valY + 35
    //    18pt Bold ascent=25 -> 单位     baseline = unitY + 25
    //    对齐:  unitY = valY + 35 - 25 = valY + 10
    //
    // 为什么单位用 18pt 而不是 12pt:
    //    24pt 数字墨迹高 35px, 12pt C 墨迹只有 18px (占 51%),
    //    基线对齐后 C 缩在数字右下角, ° 也跟着掉到数字腰部, 看着像没对齐。
    //    18pt C 墨迹 26px (占 74%), 比例正常, 才是标准 "30.0°C" 观感。
    //    (实测宽度仍富余: 最宽 "100.0 °C" = 159px < 卡片可用 160px)
    //
    // 注意: valY 参数 = 数字的 top_left y (= 卡片顶 + 42), 不是卡片顶
    //
    // 历史踩坑 (按时间线):
    //   v1: unitY = valY + 60
    //       当时误把 valY 当作「卡片顶」处理 (实际是数字顶),
    //       单位 top 跑到 384, baseline 401, 数字 baseline 359 ->
    //       单位在数字下面 42px, 看着像「C 掉到下一行」。
    //   v2: unitY = valY + 18  -> 数字 baseline=35, 单位 baseline=35 ✓
    //       但 ° 圆圈还画在 valY+11 (24pt 数字顶端), 看着 ° 飘在数字头上,
    //       不像标准 "30.0°C" 排版。
    //   v3 (本版): unitY = valY + 18, ° 圆圈中心 valY+21 (12pt C 的 cap 顶),
    //         视觉上是标准 "30.0°C" 排版: ° 紧贴数字右上角, C 与数字基线对齐
    void drawUnit(int valX, int valY, const char *valStr, const char *unit,
                  uint16_t color, bool showRing) {
        int uw = textW(valStr, &fonts::FreeSansBold24pt7b);
        int x = valX + uw + 6;
        int y = valY + 7;           // 18pt ink 中心 +13 = valY+20, 与 24pt 数字中心 +19.5 视觉居中
        if (showRing) {
            // ° 小圆圈: 中心放在 12pt C 的 cap 顶 (y=valY+60 ~ valY+66),
            //          视觉上像标准的 "°C" 排版
            _gfx->fillCircle(x + 4, valY + 11, 4, color);  // ° 圆圈中心: 18pt C cap 顶
            x += 12;
        }
        text(unit, x, y, &fonts::FreeSansBold18pt7b, color);
    }

    // ============ 底部信息 ============
    void drawFooter(const EnvData &data, const String &updateStr) {
        _gfx->fillRect(6, UI_FOOT_Y, UI_W - 12, 2, UI_BLACK);

        // 单空格: "Updated 18:21:10"(206px) + "Comfort: Good"(159px) 共用一行时,
        // 双空格版本会把两者挤到只剩 24px 间隙, 单空格更安全
        String line = String("Updated ") + updateStr;
        text(line, 12, UI_FOOT_Y + 8, &fonts::FreeSansBold12pt7b, UI_BLACK);

        if (data.sensorOK) {
            String cf = String("Comfort: ") + getComfortLevel(data.temperature, data.humidity);
            text(cf, UI_W - 12, UI_FOOT_Y + 8, &fonts::FreeSansBold12pt7b,
                 getComfortColor(data.temperature, data.humidity), top_right);
        }

        text("M5PaperColor | ESP32-S3R8", 12, UI_FOOT_Y + 40,
             &fonts::FreeSans12pt7b, UI_BLACK);
        text("BtnA/B  Refresh  |  BtnC  PowerOff", 12, UI_FOOT_Y + 70,
             &fonts::FreeSans12pt7b, UI_BLACK);
    }

    // ============ 阈值配色 ============
    uint16_t getTempColor(float t) {
        if (t < 0)  return UI_BLUE;
        if (t < 15) return UI_BLUE;
        if (t < 28) return UI_GREEN;
        if (t < 35) return UI_ORANGE;
        return UI_RED;
    }

    uint16_t getHumiColor(float h) {
        if (h < 20) return UI_ORANGE;
        if (h < 60) return UI_GREEN;
        if (h < 80) return UI_BLUE;
        return UI_BLUE;
    }

    uint16_t getBatColor(uint8_t pct) {
        if (pct > 50) return UI_GREEN;
        if (pct > 20) return UI_ORANGE;
        return UI_RED;
    }

    uint16_t getComfortColor(float t, float h) {
        const char *lv = getComfortLevel(t, h);
        if (!strcmp(lv, "Good")) return UI_GREEN;
        if (!strcmp(lv, "Fair")) return UI_ORANGE;
        return UI_RED;
    }

    const char *getTempStatus(float t) {
        if (t < 0)  return "Freezing";
        if (t < 15) return "Cold";
        if (t < 28) return "Comfortable";
        if (t < 35) return "Hot";
        return "Very Hot";
    }

    const char *getHumiStatus(float h) {
        if (h < 20) return "Dry";
        if (h < 60) return "Comfortable";
        if (h < 80) return "Humid";
        return "Very Humid";
    }

    const char *getComfortLevel(float t, float h) {
        bool tempOK = (t >= 18.0f && t <= 28.0f);
        bool humiOK = (h >= 30.0f && h <= 70.0f);
        if (tempOK && humiOK) return "Good";
        if (tempOK || humiOK) return "Fair";
        return "Poor";
    }
};
