#!/usr/bin/env python3
# 解析 M5GFX 的 Adafruit GFX 字体头文件, 计算精确排版度量
# 目的: 在改代码前先算准文字宽高/基线, 避免一次次烧录试错
import re, sys, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / ".pio/libdeps/m5stack-papercolor/M5GFX/src/lgfx/Fonts/GFXFF"


class Font:
    def __init__(self, name):
        path = os.path.join(FONT_DIR, name + ".h")
        src = open(path, encoding="utf-8", errors="ignore").read()

        # 字形表: { bitmapOffset, width, height, xAdvance, xOffset, yOffset }
        glyph_block = re.search(r"Glyphs\[\]\s*PROGMEM\s*=\s*\{(.*?)\};",
                                src, re.S).group(1)
        self.glyphs = {}
        for m in re.finditer(r"\{\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,"
                             r"\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}"
                             r"\s*,?\s*//\s*0x([0-9A-Fa-f]+)",
                             glyph_block):
            bmp, w, h, xa, xo, yo, code = m.groups()
            self.glyphs[int(code, 16)] = dict(
                w=int(w), h=int(h), xa=int(xa), xo=int(xo), yo=int(yo))

        # GFXfont 结构体末尾的 yAdvance
        tail = re.search(r"GFXfont\s+\w+\s*PROGMEM\s*=\s*\{(.*?)\};", src, re.S).group(1)
        self.yAdvance = int(tail.rsplit(",", 1)[1].strip())

        # baseline = max(-yOffset);  height = max(h-ab) + baseline
        ab = max(-g["yo"] for g in self.glyphs.values())
        bb = max(g["h"] + g["yo"] for g in self.glyphs.values())  # h - (-yo)
        self.ascent = ab
        self.height = bb + ab

    def width(self, s):
        left = right = 0
        for ch in s:
            g = self.glyphs.get(ord(ch))
            if g is None:
                g = self.glyphs.get(0x20)
            if left == 0 and right == 0 and g["xo"] < 0:
                left = right = -g["xo"]
            right = left + max(g["xa"], g["w"] + g["xo"])
            left += g["xa"]
        return right


NAMES = {
    "b9":  "FreeSansBold9pt7b",
    "b12": "FreeSansBold12pt7b",
    "b18": "FreeSansBold18pt7b",
    "b24": "FreeSansBold24pt7b",
    "r9":  "FreeSans9pt7b",
    "r12": "FreeSans12pt7b",
    "r18": "FreeSans18pt7b",
    "r24": "FreeSans24pt7b",
}
F = {k: Font(v) for k, v in NAMES.items()}


def show():
    print("font   yAdv ascent height")
    for k, f in F.items():
        print(f"{k:6} {f.yAdvance:4} {f.ascent:6} {f.height:6}")


TESTS = {
    "b24": ["26.5", "-8.3", "100.0", "--.-", "12:34", "88%"],
    "b12": ["C", "%", ":30", "TEMPERATURE", "HUMIDITY", "BATTERY", "Updated 18:21:10"],
    "b18": ["Environment Monitor"],
    "r12": ["SHT40 + RX8130CE | 4.0in E-Ink", "M5PaperColor | ESP32-S3R8",
            "BtnA/B  Refresh  |  BtnC  PowerOff", "Wednesday", "2026-08-29",
            "Range -10~40", "Comfortable", "No Sensor"],
    "b9":  ["RTC OK", "TEMPERATURE", "HUMIDITY"],
    "r9":  ["Range 20~80"],
}


def widths():
    print("\n--- text widths ---")
    for k, strs in TESTS.items():
        f = F[k]
        for s in strs:
            print(f"{k:5} {f.width(s):4}px  {s!r}")


if __name__ == "__main__":
    show()
    widths()
    if len(sys.argv) > 2:
        f = F[sys.argv[1]]
        print(f"\n{NAMES[sys.argv[1]]}: width={f.width(sys.argv[2])} ascent={f.ascent}")
