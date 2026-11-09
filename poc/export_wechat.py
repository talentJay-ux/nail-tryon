#!/usr/bin/env python3
"""Export try-on runs as WeChat-friendly share images: up to 9 single cards + one long image.

  python poc/export_wechat.py --out DIR --title "..." LABEL=RUN_DIR [LABEL=RUN_DIR ...]
      [--crop x0,y0,x1,y1]   nail-region crop as fractions of the candidate image (default 0,0.12,0.76,0.70)

Each run dir is a tryon.py output (input-hand.jpg, input-ref.jpg, cand-*.jpg). Cards are 1080 px wide.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = 1080
PAD = 24
BG = (250, 248, 245)
INK = (40, 40, 40)
MUTED = (120, 120, 120)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    sys.exit("no CJK font found; install one or add its path to FONT_CANDIDATES")


def fit(img: Image.Image, w: int, h: int | None = None) -> Image.Image:
    if h is None:
        h = round(img.height * w / img.width)
    return img.resize((w, h), Image.LANCZOS)


def cover(img: Image.Image, w: int, h: int) -> Image.Image:
    s = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def text_block(lines: list[tuple[str, int, tuple]], width: int = W) -> Image.Image:
    fonts = [(t, font(s), c) for t, s, c in lines]
    h = PAD + sum(f.getbbox("国")[3] + 14 for _, f, _ in fonts) + PAD
    im = Image.new("RGB", (width, h), BG)
    d = ImageDraw.Draw(im)
    y = PAD
    for t, f, c in fonts:
        d.text((PAD, y), t, font=f, fill=c)
        y += f.getbbox("国")[3] + 14
    return im


def stack(parts: list[Image.Image]) -> Image.Image:
    h = sum(p.height for p in parts)
    out = Image.new("RGB", (W, h), BG)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    return out


def row(images: list[Image.Image], captions: list[str], target_h: int | None = None) -> Image.Image:
    n = len(images)
    cw = (W - PAD * (n + 1)) // n
    if target_h is None:
        target_h = max(round(im.height * cw / im.width) for im in images)
    f = font(26)
    out = Image.new("RGB", (W, target_h + PAD * 2 + 40), BG)
    d = ImageDraw.Draw(out)
    x = PAD
    for im, cap in zip(images, captions):
        out.paste(cover(im, cw, target_h), (x, PAD))
        d.text((x, PAD + target_h + 8), cap, font=f, fill=MUTED)
        x += cw + PAD
    return out


def card(cand: Image.Image, crop: tuple[float, float, float, float], title: str) -> Image.New:
    x0, y0, x1, y1 = crop
    region = cand.crop((round(x0 * cand.width), round(y0 * cand.height), round(x1 * cand.width), round(y1 * cand.height)))
    zoom = fit(region, W - 2 * PAD)
    head = text_block([(title, 36, INK)])
    body = Image.new("RGB", (W, zoom.height + PAD), BG)
    body.paste(zoom, (PAD, 0))
    return stack([head, body])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="美甲试戴效果图")
    ap.add_argument("--subtitle", default="客图款式 → 顾客手上，AI 生成效果图，仅供参考")
    ap.add_argument("--crop", default="0,0.12,0.76,0.70")
    ap.add_argument("groups", nargs="+", help="LABEL=RUN_DIR")
    a = ap.parse_args()
    crop = tuple(float(v) for v in a.crop.split(","))
    a.out.mkdir(parents=True, exist_ok=True)

    groups = []
    for g in a.groups:
        label, _, d = g.partition("=")
        d = Path(d).expanduser()
        cands = sorted(d.glob("cand-*.jpg")) + sorted(d.glob("cand-*.png"))
        if not cands:
            sys.exit(f"no candidates in {d}")
        groups.append((label, d, cands))

    singles: list[tuple[str, Image.Image]] = []
    first = groups[0][1]
    hand = Image.open(first / "input-hand.jpg").convert("RGB")
    ref = Image.open(first / "input-ref.jpg").convert("RGB")
    singles.append(("01-输入对照", stack([
        text_block([(a.title, 48, INK), (a.subtitle, 26, MUTED)]),
        row([hand, ref], ["顾客手照（原图）", "客图（参考款式）"], target_h=700),
    ])))

    n = 2
    for label, d, cands in groups:
        ims = [Image.open(c).convert("RGB") for c in cands]
        singles.append((f"{n:02d}-{label}-总览", stack([
            text_block([(label, 36, INK)]),
            row(ims, [f"{label} · 候选 {i + 1}" for i in range(len(ims))], target_h=640),
        ])))
        n += 1
        for i, im in enumerate(ims):
            singles.append((f"{n:02d}-{label}-候选{i + 1}", card(im, crop, f"{label} · 候选 {i + 1} · 指甲放大")))
            n += 1

    footer = text_block([("效果图由 AI 生成（Nano Banana Pro），实际上手以到店效果为准", 24, MUTED)])

    for name, im in singles:
        im.save(a.out / f"{name}.jpg", quality=90)
    long_img = stack([im for _, im in singles] + [footer])
    long_img.save(a.out / "00-长图.jpg", quality=88)
    print(f"{len(singles)} single images + 00-长图.jpg ({long_img.width}x{long_img.height}) → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
