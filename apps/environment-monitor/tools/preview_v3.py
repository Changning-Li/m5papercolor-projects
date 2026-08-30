#!/usr/bin/env python3
"""Render and validate the layout currently implemented by ``src/env_ui.h``."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfxrender import GFXFont, Canvas, write_png

F = {n: GFXFont(n) for n in (
    "FreeSans9pt7b", "FreeSans12pt7b",
    "FreeSansBold9pt7b", "FreeSansBold12pt7b", "FreeSansBold18pt7b", "FreeSansBold24pt7b")}

W, H = 400, 600
WHITE, BLACK, RED, GREEN, BLUE, ORANGE = 0xFFFF, 0x0000, 0xF800, 0x07E0, 0x001F, 0xFC00
CYAN, GRAY = BLUE, BLACK

HEAD_H, PAD, CARD_W, CARD_L = 72, 14, 188, 6
CARD_R  = W - 6 - CARD_W
ROW1_Y  = HEAD_H + 6
ROW2_Y  = ROW1_Y + 204
CARD_H  = 200
FOOT_Y  = ROW2_Y + CARD_H + 8
AVAIL   = CARD_W - PAD * 2


def card_frame(g, x, y, accent):
    g.fill_round_rect(x, y, CARD_W, CARD_H, 8, WHITE)
    g.fill_round_rect(x, y, CARD_W, 6, 3, accent)
    g.draw_round_rect(x, y, CARD_W, CARD_H, 8, BLACK)


def draw_unit(g, valX, valY, valStr, unit, color, with_ring):
    """与 env_ui.h drawUnit 完全一致: 单位用 18pt, y = valY + 7 (视觉居中)"""
    big = F["FreeSansBold24pt7b"]
    b18 = F["FreeSansBold18pt7b"]
    x = valX + big.text_width(valStr) + 6
    y = valY + 7
    if with_ring:
        g.fill_circle(x + 4, valY + 11, 4, color)   # ° 圆圈: 18pt C cap 顶, 半径 4
        x += 12
    g.text(unit, x, y, b18, color)
    return x + b18.text_width(unit)


def render(path, d, verbose=True):
    g = Canvas(W, H, 0xFFFFFF)
    boxes = []

    def add(label, s, x, y, font, note=""):
        f = F[font]
        w = f.text_width(s)
        top, bot = f.ink_box(s)
        if bot > top:
            boxes.append((label, x, y + top, x + w, y + bot))
        if verbose:
            print(f"  {label:22s} '{s[:22]:22s}' x={x:3d} 宽={w:3d} 右边缘={x+w:3d}{note}")
        return x + w

    def add_right(label, s, right, y, font):
        f = F[font]
        return add(label, s, right - f.text_width(s), y, font)

    # ---- header ----
    g.fill_rect(0, 0, W, HEAD_H, BLACK)
    add("header/title", "Environment Monitor", 12, 8, "FreeSansBold18pt7b")
    g.text("Environment Monitor", 12, 8, F["FreeSansBold18pt7b"], WHITE)
    subtitle = "SHT40 | RX8130 | 4in E-Ink"
    status = "OK" if d["ok"] else "ERR"
    status_y = HEAD_H - 16 - 8
    add("header/subtitle", subtitle, 12, 44, "FreeSans12pt7b")
    g.text(subtitle, 12, 44, F["FreeSans12pt7b"], WHITE)
    add_right("header/status", status, W - 12, status_y, "FreeSansBold12pt7b")
    g.fill_circle(W - 62, HEAD_H - 16, 5, GREEN if d["ok"] else RED)
    g.text(status, W - 12, status_y,
           F["FreeSansBold12pt7b"], GREEN if d["ok"] else RED, "top_right")

    # ---- row2 TIME ----
    x, y = CARD_L, ROW2_Y
    card_frame(g, x, y, BLUE)
    add("TIME/label", "TIME", x + PAD, y + 16, "FreeSansBold9pt7b")
    g.text("TIME", x + PAD, y + 16, F["FreeSansBold9pt7b"], BLACK)
    g.text(d["rtcStr"], x + CARD_W - PAD, y + 16, F["FreeSansBold9pt7b"],
           GREEN if d["rtcOK"] else RED, "top_right")
    add_right("TIME/status", d["rtcStr"], x + CARD_W - PAD, y + 16, "FreeSansBold9pt7b")
    add("TIME/value", d["time"], x + PAD, y + 42, "FreeSansBold24pt7b")
    g.text(d["time"], x + PAD, y + 42, F["FreeSansBold24pt7b"], BLACK)
    secX = x + PAD + F["FreeSansBold24pt7b"].text_width(d["time"]) + 6
    sec = ":%02d" % d["sec"]
    add("TIME/seconds", sec, secX, y + 60, "FreeSansBold12pt7b")
    g.text(sec, secX, y + 60, F["FreeSansBold12pt7b"], BLACK)
    add("TIME/date", d["date"], x + PAD, y + 108, "FreeSans12pt7b")
    g.text(d["date"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    add("TIME/wday", d["wday"], x + PAD, y + 148, "FreeSans12pt7b")
    g.text(d["wday"], x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)

    # ---- row2 BATTERY ----
    x, y = CARD_R, ROW2_Y
    card_frame(g, x, y, GREEN)
    add("BAT/label", "BATTERY", x + PAD, y + 16, "FreeSansBold9pt7b")
    g.text("BATTERY", x + PAD, y + 16, F["FreeSansBold9pt7b"], BLACK)
    g.text(d["pwr"], x + CARD_W - PAD, y + 16, F["FreeSansBold9pt7b"], d["pwrCol"], "top_right")
    add_right("BAT/status", d["pwr"], x + CARD_W - PAD, y + 16, "FreeSansBold9pt7b")
    bv = "%d%%" % d["bat"]
    add("BAT/value", bv, x + PAD, y + 42, "FreeSansBold24pt7b")
    g.text(bv, x + PAD, y + 42, F["FreeSansBold24pt7b"], d["batCol"])
    add("BAT/volt", "%.2f V" % (d["mv"] / 1000.0), x + PAD, y + 108, "FreeSans12pt7b")
    g.text("%.2f V" % (d["mv"] / 1000.0), x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    bx, by = x + PAD, y + 144
    bw, bh = CARD_W - PAD * 2, 22
    g.draw_round_rect(bx, by, bw, bh, 4, BLACK)
    fillw = (bw - 6) * d["bat"] // 100
    if fillw > 0:
        g.fill_round_rect(bx + 3, by + 3, fillw, bh - 6, 2, d["batCol"])

    # ---- row1 TEMP ----
    x, y = CARD_L, ROW1_Y
    card_frame(g, x, y, ORANGE)
    add("TEMP/label", "TEMPERATURE", x + PAD, y + 16, "FreeSansBold9pt7b")
    g.text("TEMPERATURE", x + PAD, y + 16, F["FreeSansBold9pt7b"], BLACK)
    tv = "%.1f" % d["temp"]
    add("TEMP/value", tv, x + PAD, y + 42, "FreeSansBold24pt7b")
    g.text(tv, x + PAD, y + 42, F["FreeSansBold24pt7b"], d["tCol"])
    unit_x = x + PAD + F["FreeSansBold24pt7b"].text_width(tv) + 18
    add("TEMP/unit", "C", unit_x, y + 49, "FreeSansBold18pt7b")
    draw_unit(g, x + PAD, y + 42, tv, "C", d["tCol"], True)
    add("TEMP/status", d["tstatus"], x + PAD, y + 108, "FreeSans12pt7b")
    g.text(d["tstatus"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    add("TEMP/range", "Range -10~40", x + PAD, y + 148, "FreeSans12pt7b")
    g.text("Range -10~40", x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)

    # ---- row1 HUMID ----
    x, y = CARD_R, ROW1_Y
    card_frame(g, x, y, BLUE)
    add("HUMID/label", "HUMIDITY", x + PAD, y + 16, "FreeSansBold9pt7b")
    g.text("HUMIDITY", x + PAD, y + 16, F["FreeSansBold9pt7b"], BLACK)
    hv = "%.1f" % d["humi"]
    add("HUMID/value", hv, x + PAD, y + 42, "FreeSansBold24pt7b")
    g.text(hv, x + PAD, y + 42, F["FreeSansBold24pt7b"], d["hCol"])
    unit_x = x + PAD + F["FreeSansBold24pt7b"].text_width(hv) + 6
    add("HUMID/unit", "%", unit_x, y + 49, "FreeSansBold18pt7b")
    draw_unit(g, x + PAD, y + 42, hv, "%", d["hCol"], False)
    add("HUMID/status", d["hstatus"], x + PAD, y + 108, "FreeSans12pt7b")
    g.text(d["hstatus"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    add("HUMID/range", "Range 20~80", x + PAD, y + 148, "FreeSans12pt7b")
    g.text("Range 20~80", x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)

    # ---- footer ----
    g.fill_rect(6, FOOT_Y, W - 12, 2, BLACK)
    updated = "Updated " + d["updated"]
    comfort = "Comfort: " + d["comfort"]
    add("FOOT/updated", updated, 12, FOOT_Y + 8, "FreeSansBold12pt7b")
    add_right("FOOT/comfort", comfort, W - 12, FOOT_Y + 8, "FreeSansBold12pt7b")
    g.text(updated, 12, FOOT_Y + 8, F["FreeSansBold12pt7b"], BLACK)
    g.text(comfort, W - 12, FOOT_Y + 8, F["FreeSansBold12pt7b"],
           d["cfCol"], "top_right")
    add("FOOT/line2", "M5PaperColor | ESP32-S3R8", 12, FOOT_Y + 40, "FreeSans12pt7b")
    g.text("M5PaperColor | ESP32-S3R8", 12, FOOT_Y + 40, F["FreeSans12pt7b"], BLACK)
    add("FOOT/line3", "BtnA/B  Refresh  |  BtnC  PowerOff", 12, FOOT_Y + 70, "FreeSans12pt7b")
    g.text("BtnA/B  Refresh  |  BtnC  PowerOff", 12, FOOT_Y + 70, F["FreeSans12pt7b"], BLACK)

    # ---- 越界 / 重叠检查 ----
    if verbose:
        print()
    problems = []
    for lab, x0, y0, x1, y1 in boxes:
        if y1 > H or y0 < 0 or x0 < 0 or x1 > W:
            problems.append(f"{lab} 超出屏幕: x {x0}..{x1}, y {y0}..{y1}")
    # 卡片右边界检查 (每张卡片的内容都不能超过自己的卡片右沿)
    for lab, x0, y0, x1, y1 in boxes:
        if "TIME" in lab or "TEMP" in lab:
            limit_x = CARD_L + CARD_W
        elif "BAT/" in lab or "HUMID" in lab:
            limit_x = CARD_R + CARD_W
        elif "header" in lab or "FOOT" in lab:
            limit_x = W
        else:
            continue
        if x1 > limit_x:
            problems.append(f"{lab} 超出卡片右沿 ({x1} > {limit_x})")
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ix0, iy0 = max(a[1], b[1]), max(a[2], b[2])
            ix1, iy1 = min(a[3], b[3]), min(a[4], b[4])
            if ix1 > ix0 and iy1 > iy0:
                problems.append(f"重叠: {a[0]} vs {b[0]}")
                n += 1
    if verbose:
        print(f"重叠检查: {len(boxes)} 个文本框, 重叠 {n} 处")
        for p in problems:
            print(f"  !! {p}")
        if not problems:
            print("  全部通过")

    write_png(path, g)
    return problems


if __name__ == "__main__":
    d = dict(ok=True, rtcOK=True, rtcStr="RTC OK", time="18:41", sec=12,
             date="2026-08-29", wday="Saturday",
             bat=100, mv=4246, pwr="USB", pwrCol=BLUE, batCol=GREEN,
             temp=29.1, humi=57.0, tCol=ORANGE, hCol=BLUE,
             tstatus="Comfortable", hstatus="Comfortable",
             comfort="Good", cfCol=GREEN, updated="18:41:12")
    problems = render(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ui_v3.png", d)
    raise SystemExit(1 if problems else 0)
