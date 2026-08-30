#!/usr/bin/env python3
"""Render a preview of the env-monitor UI using the same numbers as src/env_ui.h."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfxrender import GFXFont, Canvas, write_png

F = {n: GFXFont(n) for n in (
    "FreeSans9pt7b", "FreeSans12pt7b", "FreeSans18pt7b",
    "FreeSansBold9pt7b", "FreeSansBold12pt7b", "FreeSansBold18pt7b", "FreeSansBold24pt7b")}

W, H = 400, 600
WHITE, BLACK, RED, GREEN, BLUE, ORANGE, YELLOW = 0xFFFF, 0x0000, 0xF800, 0x07E0, 0x001F, 0xFC00, 0xFFE0
CYAN = BLUE
GRAY = BLACK

PAD, CARD_W, CARD_L, CARD_R = 12, 188, 8, 204
ROW1_Y, ROW2_Y, CARD_H, FOOT_Y = 84, 268, 176, 452


def card_frame(g, x, y, accent):
    g.fill_round_rect(x, y, CARD_W, CARD_H, 8, WHITE)
    g.fill_round_rect(x, y, CARD_W, 6, 3, accent)
    g.draw_round_rect(x, y, CARD_W, CARD_H, 8, BLACK)


def render(path, data):
    g = Canvas(W, H, 0xFFFFFF)

    # header
    g.fill_rect(0, 0, W, 76, BLACK)
    g.text("Environment Monitor", 12, 4, F["FreeSansBold18pt7b"], WHITE)
    g.text("M5PaperColor | SHT40 | RX8130CE", 12, 48, F["FreeSans9pt7b"], WHITE)
    g.fill_circle(330, 57, 5, GREEN)
    g.text("OK", 388, 48, F["FreeSansBold9pt7b"], GREEN, "top_right")

    # ---- row 1: TIME (left) ----
    x, y = CARD_L, ROW1_Y
    card_frame(g, x, y, BLUE)
    g.text("TIME", x + PAD, y + 12, F["FreeSansBold9pt7b"], BLACK)
    g.fill_circle(x + 88, y + 21, 4, GREEN)
    g.text("RTC OK", x + CARD_W - PAD, y + 12, F["FreeSansBold9pt7b"], GREEN, "top_right")
    t = data["time"]
    g.text(t, x + PAD, y + 36, F["FreeSansBold24pt7b"], BLACK)
    secX = x + PAD + F["FreeSansBold24pt7b"].text_width(t) + 6
    g.text(":%02d" % data["sec"], secX, y + 59, F["FreeSansBold12pt7b"], GRAY)
    g.text(data["date"], x + PAD, y + 98, F["FreeSans12pt7b"], BLACK)
    g.text(data["wday"], x + PAD, y + 132, F["FreeSans12pt7b"], BLACK)
    g.fill_circle(x + CARD_W - 62, y + 143, 4, GREEN)
    g.text("RTC", x + CARD_W - PAD, y + 132, F["FreeSansBold9pt7b"], GREEN, "top_right")

    # ---- row 1: BATTERY (right) ----
    x, y = CARD_R, ROW1_Y
    card_frame(g, x, y, GREEN)
    g.text("BATTERY", x + PAD, y + 12, F["FreeSansBold9pt7b"], BLACK)
    g.text("USB", x + CARD_W - PAD, y + 12, F["FreeSansBold9pt7b"], BLUE, "top_right")
    g.text("%d%%" % data["bat"], x + PAD, y + 36, F["FreeSansBold24pt7b"], GREEN)
    g.text("%.2f V" % (data["mv"] / 1000.0), x + PAD, y + 98, F["FreeSans12pt7b"], BLACK)
    bx, by = x + PAD, y + 134
    bw, bh = CARD_W - PAD * 2, 18
    g.draw_round_rect(bx, by, bw, bh, 4, BLACK)
    g.fill_round_rect(bx + 3, by + 3, (bw - 6) * data["bat"] // 100, bh - 6, 2, GREEN)

    # ---- row 2: TEMPERATURE ----
    x, y = CARD_L, ROW2_Y
    card_frame(g, x, y, ORANGE)
    g.text("TEMPERATURE", x + PAD, y + 12, F["FreeSansBold9pt7b"], BLACK)
    tv = "%.1f" % data["temp"]
    g.text(tv, x + PAD, y + 36, F["FreeSansBold24pt7b"], ORANGE)
    ux = x + PAD + F["FreeSansBold24pt7b"].text_width(tv) + 8
    uy = y + 59
    g.draw_circle(ux + 4, y + 30, 3, ORANGE)
    g.text("C", ux + 10, uy, F["FreeSansBold12pt7b"], ORANGE)
    g.text(data["tstatus"], x + PAD, y + 98, F["FreeSans12pt7b"], BLACK)
    g.text("Range -10 ~ 40", x + PAD, y + 132, F["FreeSans12pt7b"], GRAY)

    # ---- row 2: HUMIDITY ----
    x, y = CARD_R, ROW2_Y
    card_frame(g, x, y, CYAN)
    g.text("HUMIDITY", x + PAD, y + 12, F["FreeSansBold9pt7b"], BLACK)
    hv = "%.1f" % data["humi"]
    g.text(hv, x + PAD, y + 36, F["FreeSansBold24pt7b"], BLUE)
    ux = x + PAD + F["FreeSansBold24pt7b"].text_width(hv) + 8
    g.text("%", ux + 10, y + 59, F["FreeSansBold12pt7b"], BLUE)
    g.text(data["hstatus"], x + PAD, y + 98, F["FreeSans12pt7b"], BLACK)
    g.text("Range 20 ~ 80", x + PAD, y + 132, F["FreeSans12pt7b"], GRAY)

    # ---- footer ----
    g.fill_rect(8, FOOT_Y, W - 16, 2, BLACK)
    g.text("Updated " + data["updated"], 12, FOOT_Y + 10, F["FreeSansBold12pt7b"], BLACK)
    g.text("Comfort: " + data["comfort"], W - 12, FOOT_Y + 10, F["FreeSans12pt7b"], GREEN, "top_right")
    g.text("M5PaperColor | ESP32-S3R8", 12, FOOT_Y + 46, F["FreeSans12pt7b"], BLACK)
    g.text("SHT40 + RX8130CE | 4.0in E-Ink", 12, FOOT_Y + 78, F["FreeSans12pt7b"], BLACK)
    g.text("BtnA/B Refresh | BtnC PowerOff", 12, FOOT_Y + 110, F["FreeSans12pt7b"], GRAY)

    write_png(path, g)
    return g


if __name__ == "__main__":
    data = dict(time="10:22", sec=35, date="2026-08-29", wday="Saturday",
                bat=100, mv=4248, temp=30.7, humi=68.5,
                tstatus="Hot", hstatus="Humid", comfort="Fair", updated="10:22:35")
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ui_preview.png"
    render(out, data)
    print("wrote", out)
