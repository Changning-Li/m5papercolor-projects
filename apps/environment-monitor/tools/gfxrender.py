#!/usr/bin/env python3
"""Offline preview renderer for the PaperColor env-monitor UI.

Parses the Adafruit GFX (7b) font headers shipped with M5GFX and re-implements
LovyanGFX's drawing primitives (top_left datum semantics), so the layout can be
verified on the PC before flashing.

Usage:  python3 tools/preview_layout.py [out.png]
"""
import os
import re
import sys
import zlib
import struct
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / ".pio/libdeps/m5stack-papercolor/M5GFX/src/lgfx/fonts/GFXFF"

# ---------------------------------------------------------------- font parsing
class GFXFont:
    def __init__(self, name):
        path = os.path.join(FONT_DIR, name + ".h")
        src = open(path, encoding="utf-8", errors="replace").read()

        bm = re.search(r"Bitmaps\[\]\s*PROGMEM\s*=\s*\{(.*?)\}\s*;", src, re.S)
        self.bitmap = bytes(int(x, 0) for x in re.findall(r"0x[0-9A-Fa-f]{2}|\b\d+\b", bm.group(1)))

        gm = re.search(r"Glyphs\[\]\s*PROGMEM\s*=\s*\{(.*?)\}\s*\};", src, re.S)
        rows = re.findall(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}", gm.group(1))
        self.glyphs = [(int(a), int(b), int(c), int(d), int(e), int(f)) for a, b, c, d, e, f in rows]

        fm = re.search(r"\(GFXglyph\s*\*\)\s*\w+\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*(\d+)\s*\}", src)
        self.first = int(fm.group(1), 0)
        self.last = int(fm.group(2), 0)
        self.yAdvance = int(fm.group(3))

        self.ascent = max(-g[5] for g in self.glyphs)
        self.descent = max(g[2] + g[5] for g in self.glyphs)
        self.height = self.ascent + self.descent

    def glyph(self, ch):
        idx = ord(ch) - self.first
        if idx < 0 or idx >= len(self.glyphs):
            idx = ord(' ') - self.first
        return self.glyphs[idx]

    def char_width(self, ch):
        return self.glyph(ch)[3]      # xAdvance

    def text_width(self, s):
        return sum(self.char_width(c) for c in s)

    def ink_box(self, s):
        """(top, bottom) relative to the top_left datum y, for the given string."""
        top, bot = None, None
        for c in s:
            _, w, h, _, _, yo = self.glyph(c)
            if w == 0 or h == 0:
                continue
            t = self.ascent + yo
            b = t + h
            top = t if top is None else min(top, t)
            bot = b if bot is None else max(bot, b)
        return (0, 0) if top is None else (top, bot)


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg=0xFFFFFF):
        self.w, self.h = w, h
        self.px = [bg] * (w * h)

    def _rgb(self, c565):
        r = ((c565 >> 11) & 0x1F) * 255 // 31
        g = ((c565 >> 5) & 0x3F) * 255 // 63
        b = (c565 & 0x1F) * 255 // 31
        return (r << 16) | (g << 8) | b

    def set_px(self, x, y, c565):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = self._rgb(c565)

    def fill_rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set_px(xx, yy, c)

    def rect(self, x, y, w, h, c):
        self.fill_rect(x, y, w, 1, c)
        self.fill_rect(x, y + h - 1, w, 1, c)
        self.fill_rect(x, y, 1, h, c)
        self.fill_rect(x + w - 1, y, 1, h, c)

    def fill_round_rect(self, x, y, w, h, r, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                dx = max(x + r - 1 - xx, xx - (x + w - r), 0)
                dy = max(y + r - 1 - yy, yy - (y + h - r), 0)
                if dx * dx + dy * dy <= r * r:
                    self.set_px(xx, yy, c)

    def draw_round_rect(self, x, y, w, h, r, c):
        for d in range(0, w):
            pass
        # approximate: draw 4 straight edges + corner arcs
        self.fill_rect(x + r, y, w - 2 * r, 1, c)
        self.fill_rect(x + r, y + h - 1, w - 2 * r, 1, c)
        self.fill_rect(x, y + r, 1, h - 2 * r, c)
        self.fill_rect(x + w - 1, y + r, 1, h - 2 * r, c)
        for cx, cy, sx, sy in ((x + r, y + r, -1, -1), (x + w - 1 - r, y + r, 1, -1),
                               (x + r, y + h - 1 - r, -1, 1), (x + w - 1 - r, y + h - 1 - r, 1, 1)):
            for a in range(r + 1):
                for b in range(r + 1):
                    if a * a + b * b <= r * r and (a * a + b * b) >= (r - 1) * (r - 1):
                        self.set_px(cx + sx * a, cy + sy * b, c)

    def fill_circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set_px(xx, yy, c)

    def draw_circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - 1) ** 2 <= d <= r * r:
                    self.set_px(xx, yy, c)

    # ---- text: LovyanGFX top_left semantics: baseline = y + ascent ----
    def text(self, s, x, y, font, c565, datum="top_left"):
        w = font.text_width(s)
        if datum == "top_right":
            x -= w
        elif datum == "top_center":
            x -= w // 2
        cx = x
        for ch in s:
            off, gw, gh, xa, xo, yo = font.glyph(ch)
            if gw and gh:
                top = y + font.ascent + yo
                bit = 0
                for gy in range(gh):
                    for gx in range(gw):
                        byte = font.bitmap[off + (bit >> 3)] if (off + (bit >> 3)) < len(font.bitmap) else 0
                        if byte & (0x80 >> (bit & 7)):
                            self.set_px(cx + xo + gx, top + gy, c565)
                        bit += 1
            cx += xa
        return w


# ---------------------------------------------------------------------- PNG
def write_png(path, canvas):
    raw = b""
    for y in range(canvas.h):
        row = b"\x00"
        for x in range(canvas.w):
            c = canvas.px[y * canvas.w + x]
            row += bytes((((c >> 16) & 0xFF), ((c >> 8) & 0xFF), (c & 0xFF)))
        raw += row

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)
