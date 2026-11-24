#!/usr/bin/env python3
# Copyright (c) 2026 INTENSE FINANCE, LLC
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE-GPLv3.txt in this tools package, or
# https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt
#
"""Compose Grobie Master Character Sheet v2 from approved canonical stills.

Contain-fit only: uniform scale, no crop, no stretch, no AI regeneration.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

def default_kit() -> Path:
    env = os.environ.get("GROBIE_KIT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "kit"

KIT = default_kit()
OUT_4K = KIT / "grobie-character-sheet-v2-4k.png"
OUT_JPG = KIT / "grobie-character-sheet-v2.jpg"

W, H = 3840, 2160
BG = (0x16, 0x19, 0x22)
HEADER_BG = (0x12, 0x15, 0x1C)
CARD = (0x20, 0x25, 0x34)
CARD_BORDER = (0x3A, 0x42, 0x58)
SWATCH_BORDER = (0x6A, 0x73, 0x8A)
GOLD = (0xC2, 0x9E, 0x7C)
GOLD_DIM = (0x8A, 0x72, 0x58)
WHITE = (0xF7, 0xF4, 0xEE)
MUTE = (0xC8, 0xCB, 0xD6)
INK = (0xE6, 0xE8, 0xF0)
WELL = (0x12, 0x14, 0x1C)
SWATCHES = [
    ((0x13, 0x18, 0x2B), "#13182B", "Navy Coat"),
    ((0xC2, 0x9E, 0x7C), "#C29E7C", "Gold Trim"),
    ((0x34, 0x37, 0x4B), "#34374B", "Glass Blue"),
    ((0xF3, 0xDB, 0xBC), "#F3DBBC", "Core Glow"),
    ((0xFE, 0xF7, 0xF0), "#FEF7F0", "Eye Glow"),
]

def _font_dir() -> Path:
    env = os.environ.get("GROBIE_FONT_DIR")
    if env:
        return Path(env)
    for d in (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/dejavu"),
        Path("/usr/local/share/fonts"),
    ):
        if (d / "DejaVuSans-Bold.ttf").is_file():
            return d
    return Path("/usr/share/fonts/truetype/dejavu")

_FONT_DIR = _font_dir()
FONT_BOLD = str(_FONT_DIR / "DejaVuSans-Bold.ttf")
FONT_REG = str(_FONT_DIR / "DejaVuSans.ttf")
FONT_MONO = str(_FONT_DIR / "DejaVuSansMono-Bold.ttf")
RESAMPLE = Image.Resampling.LANCZOS


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=fnt)
    return x1 - x0, y1 - y0


def contain(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    if im.mode != "RGB":
        im = im.convert("RGB")
    iw, ih = im.size
    scale = min(box_w / iw, box_h / ih)
    nw = max(1, min(box_w, int(round(iw * scale))))
    nh = max(1, min(box_h, int(round(ih * scale))))
    if (nw, nh) == (iw, ih):
        return im
    return im.resize((nw, nh), RESAMPLE)


def contain_size(iw: int, ih: int, box_w: int, box_h: int) -> tuple[int, int]:
    scale = min(box_w / iw, box_h / ih)
    return max(1, min(box_w, int(round(iw * scale)))), max(1, min(box_h, int(round(ih * scale))))


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=max(0, radius), fill=255)
    return m


def paste_centered(canvas, im, box, radius=6):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    fitted = contain(im, bw, bh)
    px = x0 + (bw - fitted.width) // 2
    py = y0 + (bh - fitted.height) // 2
    if radius > 0:
        mask = rounded_mask(fitted.size, min(radius, fitted.width // 8, fitted.height // 8))
        canvas.paste(fitted, (px, py), mask)
    else:
        canvas.paste(fitted, (px, py))
    return px, py, px + fitted.width, py + fitted.height


def draw_card(draw, box, radius=18, fill=CARD, outline=CARD_BORDER, width=2):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill, outline=outline, width=width)


def caption_bar(draw, box, lines, fnt, color=WHITE):
    """Draw one or more caption lines, vertically centered, with a gold rule at the bottom."""
    x0, y0, x1, y1 = box
    max_w = x1 - x0 - 48
    if isinstance(lines, str):
        lines = [lines]
    fitted_font = fnt
    sizes = []
    for line in lines:
        f = fnt
        tw, th = text_size(draw, line, f)
        size = f.size
        while tw > max_w and size > 15:
            size -= 1
            f = font(FONT_BOLD, size)
            tw, th = text_size(draw, line, f)
        sizes.append((line, f, tw, th))
        fitted_font = f
    total_h = sum(th for *_, th in sizes) + (len(sizes) - 1) * 4
    ty = y0 + (y1 - y0 - 4 - total_h) // 2
    for line, f, tw, th in sizes:
        draw.text((x0 + 24, ty), line, font=f, fill=color)
        ty += th + 4
    ry = y1 - 3
    draw.line((x0 + 18, ry, x1 - 18, ry), fill=GOLD, width=2)


def load(name: str) -> Image.Image:
    im = Image.open(KIT / name)
    im.load()
    return im.convert("RGB")


def build() -> Image.Image:
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    f_title = font(FONT_BOLD, 54)
    f_meta = font(FONT_REG, 30)
    f_cap = font(FONT_BOLD, 24)
    f_cap_sm = font(FONT_BOLD, 21)
    f_panel_title = font(FONT_BOLD, 26)
    f_spec_label = font(FONT_BOLD, 26)
    f_spec = font(FONT_REG, 25)
    f_swatch_hex = font(FONT_MONO, 22)
    f_swatch_name = font(FONT_REG, 20)
    f_thumb_cap = font(FONT_REG, 20)

    # --- Header ---
    header_h = 130
    draw.rectangle((0, 0, W, header_h), fill=HEADER_BG)
    title = "GROBIE  —  MASTER CHARACTER SHEET v2"
    meta = "SpaceXSI Grok Bot  ·  MAIN BOT  ·  Admiral  ·  CC0 1.0  ·  PG-13"
    tw, th = text_size(draw, title, f_title)
    mw, mh = text_size(draw, meta, f_meta)
    draw.text((64, (header_h - th) // 2 - 2), title, font=f_title, fill=WHITE)
    draw.text((W - 64 - mw, (header_h - mh) // 2), meta, font=f_meta, fill=GOLD)
    draw.rectangle((0, header_h - 3, W, header_h), fill=GOLD)

    # --- Main grid ---
    margin_x = 56
    margin_top = 40
    margin_bot = 48
    gx0 = margin_x
    gy0 = header_h + margin_top
    gx1 = W - margin_x
    gy1 = H - margin_bot
    grid_w = gx1 - gx0
    grid_h = gy1 - gy0

    gap = 36
    left_w = int(round(grid_w * 0.42))
    left_w -= left_w % 2
    right_x = gx0 + left_w + gap
    right_w = gx1 - right_x

    cap_h = 60
    pad = 18
    inner_gap = 28
    card_gap = 24

    # Left portraits hug 3:4 wells; leftover height goes to specs
    specs_min = 560
    portraits_budget = grid_h - specs_min - inner_gap
    portrait_w = (left_w - card_gap) // 2
    portrait_w -= portrait_w % 2
    well_w = portrait_w - pad * 2
    well_h = int(round(well_w * 4 / 3))
    portrait_card_h = cap_h + well_h + pad
    if portrait_card_h > portraits_budget:
        well_h = portraits_budget - cap_h - pad
        well_w = int(round(well_h * 3 / 4))
        portrait_card_h = cap_h + well_h + pad
    portraits_h = portrait_card_h
    specs_h = grid_h - portraits_h - inner_gap

    def portrait_card(box, title, im):
        draw_card(draw, box)
        x0, y0, x1, y1 = box
        caption_bar(draw, (x0, y0, x1, y0 + cap_h), title, f_cap)
        ww, hh = well_w, well_h
        wx0 = x0 + (x1 - x0 - ww) // 2
        wy0 = y0 + cap_h
        wx1, wy1 = wx0 + ww, wy0 + hh
        draw.rounded_rectangle((wx0, wy0, wx1, wy1), radius=8, fill=WELL)
        placed = paste_centered(canvas, im, (wx0, wy0, wx1, wy1), radius=6)
        ix0, iy0, ix1, iy1 = placed
        draw.rounded_rectangle((ix0, iy0, ix1 - 1, iy1 - 1), radius=6, outline=CARD_BORDER, width=1)

    p1 = (gx0, gy0, gx0 + portrait_w, gy0 + portrait_card_h)
    p2x = gx0 + portrait_w + card_gap
    p2 = (p2x, gy0, p2x + portrait_w, gy0 + portrait_card_h)
    portrait_card(p1, "OUTFIT, COLLAR  &  BADGE LOCK", load("grobie-outfit-master-v2-4k.png"))
    portrait_card(p2, "PRIMARY BODY PROPORTIONS  (6'2\"  ·  ~6.8 HEADS)", load("grobie-proportions-master-v1.jpg"))

    # --- Specs panel ---
    specs_y0 = gy0 + portraits_h + inner_gap
    specs_box = (gx0, specs_y0, gx0 + left_w, gy1)
    draw_card(draw, specs_box)
    sx0, sy0, sx1, sy1 = specs_box
    caption_bar(draw, (sx0, sy0, sx1, sy0 + cap_h), "LOCKED SPECS  &  PALETTE", f_panel_title)

    sw_pad_x = 28
    sw_top = sy0 + cap_h + 24
    sw_area_w = sx1 - sx0 - sw_pad_x * 2
    n = 5
    sw_gap = 18
    sw_w = (sw_area_w - sw_gap * (n - 1)) // n
    sw_h = 86
    for i, (color, hexcode, name) in enumerate(SWATCHES):
        x = sx0 + sw_pad_x + i * (sw_w + sw_gap)
        y = sw_top
        draw.rounded_rectangle((x, y, x + sw_w, y + sw_h), radius=8, fill=color, outline=SWATCH_BORDER, width=2)
        hx, hy = text_size(draw, hexcode, f_swatch_hex)
        nx, ny = text_size(draw, name, f_swatch_name)
        draw.text((x + (sw_w - hx) // 2, y + sw_h + 10), hexcode, font=f_swatch_hex, fill=GOLD)
        draw.text((x + (sw_w - nx) // 2, y + sw_h + 10 + hy + 4), name, font=f_swatch_name, fill=MUTE)

    # Hand-wrapped bullets so quotes and phrases stay intact
    bullets = [
        ("Proportions: ", [
            "6 ft 2 in (188 cm), ~6.8 heads tall, slim build, long legs, knee-length coat.",
        ]),
        ("Locked Marks: ", [
            "White-on-top yin-yang on upper-left chest (~19% width),",
            "stand-up V-collar with gold 8-pt stars, gold fringe epaulettes, 2-band + star cuffs.",
        ]),
        ("Never-Do: ", [
            "No hair, no human skin, no beard, no bones/skeleton, no text in frame,",
            "gold-lit mouth interior only (no pink tongue).",
        ]),
        ("Voice & Mandatory Line: ", [
            "Spoken \"Groby\" (GROH-bee). D-minor chord baritone, fully dry.",
            "First video line: \"I am Groby. The anchor holds, and so do I.\"",
        ]),
        ("Full 4K Kit, Audio & Packs: ", [
            "https://grobie.slopcore.army/",
        ]),
    ]
    hx, hy = text_size(draw, "#000000", f_swatch_hex)
    nx, ny = text_size(draw, "Navy Coat", f_swatch_name)
    bullets_y = sw_top + sw_h + 10 + hy + 4 + ny + 22
    bx0 = sx0 + 28
    y = bullets_y
    line_gap = 6
    item_gap = 18
    for label, body_lines in bullets:
        prefix = "•  " + label
        lw, lh = text_size(draw, prefix, f_spec_label)
        draw.text((bx0, y), prefix, font=f_spec_label, fill=GOLD)
        # First body line on the same row as the label when it fits
        first = body_lines[0]
        fw, fh = text_size(draw, first, f_spec)
        row_h = max(lh, fh)
        if lw + 10 + fw <= (sx1 - 28 - bx0):
            draw.text((bx0 + lw + 10, y + (row_h - fh) // 2), first, font=f_spec, fill=INK)
            y += row_h + line_gap
            rest = body_lines[1:]
        else:
            y += lh + line_gap
            rest = body_lines
        indent = bx0 + 22  # hanging indent under the label
        for line in rest:
            _, bh = text_size(draw, line, f_spec)
            draw.text((indent, y), line, font=f_spec, fill=INK)
            y += bh + line_gap
        y += item_gap

    # --- Right zone ---
    # Bottom row needs a two-line caption on the viseme card, so use a shared taller cap.
    bot_cap_h = 84
    right_gaps = 2 * inner_gap
    right_avail = grid_h - right_gaps
    # Slightly favor the 16:9 plates so they can be larger, while keeping a usable bottom shelf
    top_h = int(round(right_avail * 0.355))
    mid_h = int(round(right_avail * 0.355))
    bot_h = right_avail - top_h - mid_h

    def widescreen_card(y0, height, title, im):
        """Full-width right-zone card; 16:9 art is contain-fit and cinema-matted (no crop)."""
        box = (right_x, y0, right_x + right_w, y0 + height)
        draw_card(draw, box)
        caption_bar(draw, (right_x, y0, right_x + right_w, y0 + cap_h), title, f_cap)
        well = (right_x + pad, y0 + cap_h, right_x + right_w - pad, y0 + height - pad)
        # Darker inset reads as an intentional widescreen matte, not leftover space
        draw.rounded_rectangle(well, radius=8, fill=WELL)
        placed = paste_centered(canvas, im, well, radius=4)
        ix0, iy0, ix1, iy1 = placed
        # Gold-dim hairline around the actual plate so the matte feels deliberate
        draw.rounded_rectangle((ix0 - 2, iy0 - 2, ix1 + 1, iy1 + 1), radius=6, outline=GOLD_DIM, width=2)
        draw.rounded_rectangle((ix0, iy0, ix1 - 1, iy1 - 1), radius=4, outline=CARD_BORDER, width=1)
        return box

    head = load("grobie-head-turnaround-v2-4k.png")
    shine = load("grobie-turnaround-shine-v2-4k.png")
    widescreen_card(
        gy0,
        top_h,
        "HEAD TURNAROUND LOCK  (FRONT  ·  3/4  ·  PROFILE  ·  BACK)",
        head,
    )
    widescreen_card(
        gy0 + top_h + inner_gap,
        mid_h,
        "FULL-BODY TURNAROUND  &  ENERGY CORE",
        shine,
    )

    # Bottom row: viseme (square, no corner-clip on the 3x3) + extras
    bx0, by0, bx1, by1 = right_x, gy1 - bot_h, right_x + right_w, gy1
    bot_gap = 24
    # Size the viseme card so the well is a square that fits under the two-line caption
    vis_well = by1 - by0 - bot_cap_h - pad
    vis_card_w = vis_well + pad * 2
    # Leave at least 56% of the row for the two extras thumbs
    vis_card_w = min(vis_card_w, int(right_w * 0.46))
    # If we had to shrink width, shrink the well to stay square and centered
    vis_box = (bx0, by0, bx0 + vis_card_w, by1)
    ex_box = (bx0 + vis_card_w + bot_gap, by0, bx1, by1)

    draw_card(draw, vis_box)
    vx0, vy0, vx1, vy1 = vis_box
    caption_bar(
        draw,
        (vx0, vy0, vx1, vy0 + bot_cap_h),
        ["9-VISEME SPEECH SHEET", "(CELL 8 TONGUE  →  GOLD LIGHT)"],
        f_cap_sm,
    )
    # Square well, centered, with comfortable padding so rounded corners don't clip cells
    avail_w = vx1 - vx0 - pad * 2
    avail_h = vy1 - (vy0 + bot_cap_h) - pad
    side = min(avail_w, avail_h)
    wx0 = vx0 + (vx1 - vx0 - side) // 2
    wy0 = vy0 + bot_cap_h
    vwell = (wx0, wy0, wx0 + side, wy0 + side)
    draw.rounded_rectangle(vwell, radius=6, fill=WELL)
    # No rounded clip on the viseme grid itself — every cell must stay fully visible
    mouth = load("grobie-mouth-shapes-v3-4k.png")
    placed = paste_centered(canvas, mouth, vwell, radius=0)
    ix0, iy0, ix1, iy1 = placed
    draw.rectangle((ix0, iy0, ix1 - 1, iy1 - 1), outline=CARD_BORDER, width=1)

    draw_card(draw, ex_box)
    ex0, ey0, ex1, ey1 = ex_box
    caption_bar(
        draw,
        (ex0, ey0, ex1, ey0 + bot_cap_h),
        "ANCHOR GAG  &  LOOK DIRECTION EXTRAS",
        f_cap,
    )
    grabs = load("grobie-grabs-anchor-v2.jpg")
    mech = load("grobie-cyber-mech-v1.jpg")
    thumb_captions = [
        'Anchor Pack:  "Grobie don\'t miss."',
        "Cyber-Mech Look Basis  —  Sec. 9",
    ]
    cap_space = 48
    area = (ex0 + pad, ey0 + bot_cap_h, ex1 - pad, ey1 - pad)
    ax0, ay0, ax1, ay1 = area
    area_w = ax1 - ax0
    area_h = ay1 - ay0
    thumb_gap = 22
    col_w = (area_w - thumb_gap) // 2
    thumb_well_h = area_h - cap_space

    def thumb(col_x, im, caption):
        well = (col_x, ay0, col_x + col_w, ay0 + thumb_well_h)
        draw.rounded_rectangle(well, radius=8, fill=WELL)
        placed = paste_centered(canvas, im, well, radius=6)
        ix0, iy0, ix1, iy1 = placed
        draw.rounded_rectangle((ix0, iy0, ix1 - 1, iy1 - 1), radius=6, outline=CARD_BORDER, width=1)
        cf = f_thumb_cap
        tw, th = text_size(draw, caption, cf)
        size = cf.size
        while tw > col_w - 8 and size > 14:
            size -= 1
            cf = font(FONT_REG, size)
            tw, th = text_size(draw, caption, cf)
        cx = col_x + (col_w - tw) // 2
        cy = ay0 + thumb_well_h + 10
        draw.text((cx, cy), caption, font=cf, fill=MUTE)

    thumb(ax0, grabs, thumb_captions[0])
    thumb(ax0 + col_w + thumb_gap, mech, thumb_captions[1])

    return canvas


def main():
    global KIT, OUT_4K, OUT_JPG
    ap = argparse.ArgumentParser(description="Compose Grobie Master Character Sheet v2 from approved canonical stills.")
    ap.add_argument("--kit", help="folder of canonical stills (default: $GROBIE_KIT or ./kit next to this script)")
    ap.add_argument("--out-dir", help="output folder (default: the kit folder)")
    args = ap.parse_args()
    if args.kit:
        KIT = Path(args.kit)
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = KIT
    OUT_4K = out_dir / "grobie-character-sheet-v2-4k.png"
    OUT_JPG = out_dir / "grobie-character-sheet-v2.jpg"

    print("Building 4K character sheet…")
    img = build()
    assert img.size == (W, H), img.size
    img.save(OUT_4K, format="PNG", optimize=False, compress_level=6)
    print(f"Wrote {OUT_4K}  {OUT_4K.stat().st_size} bytes  {img.size}")
    jpg = img.resize((1920, 1080), RESAMPLE)
    jpg.save(OUT_JPG, format="JPEG", quality=93, optimize=True, subsampling=0)
    print(f"Wrote {OUT_JPG}  {OUT_JPG.stat().st_size} bytes  {jpg.size}")


if __name__ == "__main__":
    main()
