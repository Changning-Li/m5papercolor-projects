#!/usr/bin/env python3
"""Preview the new env-monitor UI (proposed layout v2)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfxrender import GFXFont, Canvas, write_png

F = {n: GFXFont(n) for n in (
    "FreeSans9pt7b", "FreeSans12pt7b", "FreeSans18pt7b",
    "FreeSansBold9pt7b", "FreeSansBold12pt7b", "FreeSansBold18pt7b", "FreeSansBold24pt7b")}

W, H = 400, 600
WHITE, BLACK, RED, GREEN, BLUE, ORANGE, YELLOW = 0xFFFF, 0x0000, 0xF800, 0x07E0, 0x001F, 0xFC00, 0xFFE0
CYAN, GRAY = BLUE, BLACK

# ========== layout constants (must match C++) ==========
HEAD_H   = 72
PAD      = 14
CARD_W   = 188
CARD_L   = 6
CARD_R   = W - 6 - CARD_W
ROW1_Y   = HEAD_H + 6
ROW2_Y   = ROW1_Y + 204
CARD_H   = 200
FOOT_Y   = ROW2_Y + CARD_H + 8


def card_frame(g, x, y, accent):
    g.fill_round_rect(x, y, CARD_W, CARD_H, 8, WHITE)
    g.fill_round_rect(x, y, CARD_W, 6, 3, accent)
    g.draw_round_rect(x, y, CARD_W, CARD_H, 8, BLACK)


def unit(g, x, y, font_big, value_str, unit_str, color, with_ring):
    """Draw small unit string right of big value (baseline aligned)."""
    big = F[font_big]
    base_y = y + big.ascent
    ux = x + big.text_width(value_str) + 8
    uy = base_y - F["FreeSansBold12pt7b"].ascent
    if with_ring:
        # small degree circle
        g.draw_circle(ux + 4, y + big.ascent - 8, 4, color)
        ux += 12
    g.text(unit_str, ux, uy, F["FreeSansBold12pt7b"], color)
    return ux + F["FreeSansBold12pt7b"].text_width(unit_str)


def render(path, data):
    g = Canvas(W, H, 0xFFFFFF)

    # ========== header ==========
    g.fill_rect(0, 0, W, HEAD_H, BLACK)
    g.text("Environment Monitor", 12, 8, F["FreeSansBold18pt7b"], WHITE)
    g.text("SHT40 + RX8130CE | 4.0in E-Ink", 12, 44, F["FreeSans12pt7b"], WHITE)
    # status pill
    ok = data["ok"]
    g.fill_circle(W - 60, HEAD_H // 2, 5, GREEN if ok else RED)
    g.text("OK" if ok else "ERR", W - 12, HEAD_H // 2 - F["FreeSansBold12pt7b"].ascent,
           F["FreeSansBold12pt7b"], GREEN if ok else RED, "top_right")

    # ========== row 1: TIME ==========
    x, y = CARD_L, ROW1_Y
    card_frame(g, x, y, BLUE)
    g.text("TIME", x + PAD, y + 16, F["FreeSansBold12pt7b"], BLACK)
    g.text("RTC OK" if data["rtcOK"] else "RTC ERR", x + CARD_W - PAD, y + 16,
           F["FreeSansBold12pt7b"], GREEN if data["rtcOK"] else RED, "top_right")
    big = data["time"]
    g.text(big, x + PAD, y + 42, F["FreeSansBold24pt7b"], BLACK)
    # seconds (smaller, baseline aligned)
    secX = x + PAD + F["FreeSansBold24pt7b"].text_width(big) + 4
    g.text(":%02d" % data["sec"], secX, y + 60, F["FreeSansBold12pt7b"], BLACK)
    g.text(data["date"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    g.text(data["wday"], x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)
    g.text(data["rtcOK"] and "RTC locked" or "RTC lost", x + CARD_W - PAD, y + 148,
           F["FreeSansBold12pt7b"], GREEN if data["rtcOK"] else RED, "top_right")

    # ========== row 1: BATTERY ==========
    x, y = CARD_R, ROW1_Y
    card_frame(g, x, y, GREEN)
    g.text("BATTERY", x + PAD, y + 16, F["FreeSansBold12pt7b"], BLACK)
    g.text(data["pwr"], x + CARD_W - PAD, y + 16, F["FreeSansBold12pt7b"], data["pwrCol"], "top_right")
    bv = "%d%%" % data["bat"]
    g.text(bv, x + PAD, y + 42, F["FreeSansBold24pt7b"], data["batCol"])
    g.text("%.2f V" % (data["mv"] / 1000.0), x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    # bar
    bx, by = x + PAD, y + 144
    bw, bh = CARD_W - PAD * 2, 22
    g.draw_round_rect(bx, by, bw, bh, 4, BLACK)
    fillw = (bw - 6) * data["bat"] // 100
    if fillw > 0:
        g.fill_round_rect(bx + 3, by + 3, fillw, bh - 6, 2, data["batCol"])

    # ========== row 2: TEMPERATURE ==========
    x, y = CARD_L, ROW2_Y
    card_frame(g, x, y, ORANGE)
    g.text("TEMPERATURE", x + PAD, y + 16, F["FreeSansBold12pt7b"], BLACK)
    tv = "%.1f" % data["temp"]
    g.text(tv, x + PAD, y + 42, F["FreeSansBold24pt7b"], data["tCol"])
    unit(g, x + PAD, y + 42, "FreeSansBold24pt7b", tv, "C", data["tCol"], True)
    g.text(data["tstatus"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    g.text("Range  -10  ~  40", x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)

    # ========== row 2: HUMIDITY ==========
    x, y = CARD_R, ROW2_Y
    card_frame(g, x, y, BLUE)
    g.text("HUMIDITY", x + PAD, y + 16, F["FreeSansBold12pt7b"], BLACK)
    hv = "%.1f" % data["humi"]
    g.text(hv, x + PAD, y + 42, F["FreeSansBold24pt7b"], data["hCol"])
    unit(g, x + PAD, y + 42, "FreeSansBold24pt7b", hv, "%", data["hCol"], False)
    g.text(data["hstatus"], x + PAD, y + 108, F["FreeSans12pt7b"], BLACK)
    g.text("Range  20  ~  80", x + PAD, y + 148, F["FreeSans12pt7b"], BLACK)

    # ========== footer ==========
    g.fill_rect(6, FOOT_Y, W - 12, 2, BLACK)
    g.text("Updated  " + data["updated"], 12, FOOT_Y + 8, F["FreeSansBold12pt7b"], BLACK)
    g.text("Comfort:  " + data["comfort"], W - 12, FOOT_Y + 8, F["FreeSansBold12pt7b"],
           data["cfCol"], "top_right")
    g.text("M5PaperColor  |  ESP32-S3R8", 12, FOOT_Y + 40, F["FreeSans12pt7b"], BLACK)
    g.text("BtnA/B  Refresh  |  BtnC  PowerOff", 12, FOOT_Y + 70, F["FreeSans12pt7b"], BLACK)

    # === overlap check ===
    boxes = []  # (label, y0, y1, x0, x1)

    def add(label, x0, y0, x1, y1, font, s):
        top, bot = F[font].ink_box(s) if s else (0, 0)
        if bot > top:
            boxes.append((label, x0, y0 + top, x0 + F[font].text_width(s), y0 + bot))
    add("title",      12,  8, 0, 0, "FreeSansBold18pt7b", "Environment Monitor")
    add("subtitle",  12, 44, 0, 0, "FreeSans12pt7b", "SHT40 + RX8130CE | 4.0in E-Ink")
    for cx, cy, lab, s in [(CARD_L, ROW1_Y, "TIME", "TIME"), (CARD_R, ROW1_Y, "BATTERY", "BATTERY"),
                            (CARD_L, ROW2_Y, "TEMP", "TEMPERATURE"), (CARD_R, ROW2_Y, "HUMI", "HUMIDITY")]:
        add(lab, cx + PAD, cy + 16, 0, 0, "FreeSansBold12pt7b", s)
    add("FOOT1", 12, FOOT_Y + 8, 0, 0, "FreeSansBold12pt7b", "Updated  " + data["updated"])
    add("FOOT2", 12, FOOT_Y + 40, 0, 0, "FreeSans12pt7b", "M5PaperColor  |  ESP32-S3R8")
    add("FOOT3", 12, FOOT_Y + 70, 0, 0, "FreeSans12pt7b", "BtnA/B  Refresh  |  BtnC  PowerOff")

    overlaps = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ix0, iy0 = max(a[1], b[1]), max(a[2], b[2])
            ix1, iy1 = min(a[3], b[3]), min(a[4], b[4])
            if ix1 > ix0 and iy1 > iy0:
                print(f"OVERLAP: {a[0]!r} {a[1:5]} vs {b[0]!r} {b[1:5]}")
                overlaps += 1
    print(f"checked {len(boxes)} boxes, overlaps: {overlaps}")

    write_png(path, g)


if __name__ == "__main__":
    data = dict(ok=True, rtcOK=True, time="10:22", sec=35, date="2026-08-29", wday="Saturday",
                bat=100, mv=4248, pwr="USB", pwrCol=BLUE, batCol=GREEN,
                temp=30.7, humi=68.5,
                tCol=ORANGE, hCol=BLUE,
                tstatus="Hot", hstatus="Humid",
                comfort="Fair", cfCol=ORANGE,
                updated="10:22:35")
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ui_v2.png"
    render(out, data)
    print("wrote", out)
