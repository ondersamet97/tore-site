#!/usr/bin/env python3
"""töre işaretinin PNG çıktılarını üretir. Dış bağımlılık yok.

Kullanım: python3 -I tools/make_icons.py
Geometri brand/tore-mark.svg ile aynıdır (120 birimlik kare).
"""
import os
import struct
import zlib

INK = (0x0F, 0x11, 0x15)
PAPER = (0xF6, 0xF6, 0xF3)
ACCENT = (0x2B, 0x4E, 0xFF)

DOTS = ((36.0, 77.0, 9.0), (61.0, 77.0, 9.0))
BAR = (82.0, 34.0, 12.0, 52.0, 3.0)  # x, y, genişlik, yükseklik, köşe yarıçapı


def in_round_rect(x, y, rx, ry, w, h, r):
    if x < rx or x > rx + w or y < ry or y > ry + h:
        return False
    dx = max(rx + r - x, x - (rx + w - r), 0.0)
    dy = max(ry + r - y, y - (ry + h - r), 0.0)
    return dx * dx + dy * dy <= r * r


def sample(x, y, bg, dot, corner):
    """Birim koordinattaki bir noktanın rengi ve saydamlığı."""
    if corner > 0 and not in_round_rect(x, y, 0.0, 0.0, 120.0, 120.0, corner):
        return (0, 0, 0, 0)
    if in_round_rect(x, y, *BAR):
        return ACCENT + (255,)
    for cx, cy, r in DOTS:
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return dot + (255,)
    return bg + (255,)


def near_edge(u, v, step, corner):
    """Bu pikselin bir kenara yakın olup olmadığı (yakınsa çoklu örnekleme gerekir)."""
    pad = step * 1.5
    bx, by, bw, bh, _ = BAR
    if bx - pad <= u <= bx + bw + pad and by - pad <= v <= by + bh + pad:
        return True
    for cx, cy, r in DOTS:
        if abs(u - cx) <= r + pad and abs(v - cy) <= r + pad:
            return True
    if corner > 0:
        edge = corner + pad
        if (u < edge or u > 120 - edge) and (v < edge or v > 120 - edge):
            return True
        if u < pad or u > 120 - pad or v < pad or v > 120 - pad:
            return True
    return False


def render(size, bg, dot, corner=0.0, ss=4):
    step = 120.0 / size
    rows = []
    for py in range(size):
        row = bytearray()
        v0 = py * step
        for px in range(size):
            u0 = px * step
            if not near_edge(u0 + step / 2, v0 + step / 2, step, corner):
                row += bytes(sample(u0 + step / 2, v0 + step / 2, bg, dot, corner))
                continue
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    r, g, b, a = sample(u0 + (sx + 0.5) * step / ss, v0 + (sy + 0.5) * step / ss, bg, dot, corner)
                    acc[0] += r * a
                    acc[1] += g * a
                    acc[2] += b * a
                    acc[3] += a
            n = ss * ss
            if acc[3] == 0:
                row += b"\x00\x00\x00\x00"
            else:
                row += bytes((round(acc[0] / acc[3]), round(acc[1] / acc[3]), round(acc[2] / acc[3]), round(acc[3] / n)))
        rows.append(bytes(row))
    return rows


def render_canvas(width, height, mark, ss=4):
    """Mürekkep zeminli geniş tuval; işaret ortada (bağlantı önizleme görseli için)."""
    step = 120.0 / mark
    ox = (width - mark) / 2.0
    oy = (height - mark) / 2.0
    rows = []
    for py in range(height):
        row = bytearray()
        for px in range(width):
            u0 = (px - ox) * step
            v0 = (py - oy) * step
            if not near_edge(u0 + step / 2, v0 + step / 2, step, 0.0):
                row += bytes(sample(u0 + step / 2, v0 + step / 2, INK, PAPER, 0.0))
                continue
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    r, g, b, _ = sample(u0 + (sx + 0.5) * step / ss, v0 + (sy + 0.5) * step / ss, INK, PAPER, 0.0)
                    acc[0] += r
                    acc[1] += g
                    acc[2] += b
            n = ss * ss
            row += bytes((round(acc[0] / n), round(acc[1] / n), round(acc[2] / n), 255))
        rows.append(bytes(row))
    return rows


def write_png(path, rows, width, height, alpha):
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = bytearray()
    for row in rows:
        raw.append(0)
        if alpha:
            raw += row
        else:
            raw += bytes(b for i, b in enumerate(row) if i % 4 != 3)
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brand")
    jobs = (
        ("tore-logo-400.png", 400, INK, PAPER, 0.0),
        ("tore-logo-800.png", 800, INK, PAPER, 0.0),
        ("tore-logo-light-400.png", 400, PAPER, INK, 0.0),
        ("icon-180.png", 180, INK, PAPER, 0.0),
        ("icon-32.png", 32, INK, PAPER, 26.0),
    )
    for name, size, bg, dot, corner in jobs:
        rows = render(size, bg, dot, corner)
        write_png(os.path.join(out, name), rows, size, size, alpha=corner > 0)
        print(name, size, os.path.getsize(os.path.join(out, name)), "bayt")
    og = os.path.join(out, "og-1200x630.png")
    write_png(og, render_canvas(1200, 630, 360), 1200, 630, alpha=False)
    print("og-1200x630.png", os.path.getsize(og), "bayt")


if __name__ == "__main__":
    main()
