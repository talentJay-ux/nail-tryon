#!/usr/bin/env python3
"""Deterministic photo clean-up so a dim, noisy hand photo reads like a bright reference shot.

  python poc/beautify.py IMG [IMG ...] --out DIR [--wall-target 0.93] [--lift 1.0] [--denoise 5] [--warmth 0.0]

Steps (all global, no generative model, so nail hue is preserved):
  1. white balance from the brightest neutral region (the backdrop) so greys are grey
  2. exposure lift with a soft shoulder, aiming the backdrop at --wall-target (0..1)
  3. mild non-local-means denoise, then light unsharp mask
Writes DIR/<name>.jpg and prints the median nail-free backdrop level before/after.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def estimate_backdrop(img: np.ndarray) -> np.ndarray:
    """Median colour of bright, low-saturation pixels (the wall), float 0..1 RGB."""
    f = img.astype(np.float32) / 255.0
    hsv = cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0
    mask = (sat < 0.12) & (val > np.percentile(val, 60))
    if mask.sum() < 500:
        mask = val > np.percentile(val, 80)
    return np.median(f[mask], axis=0)


def process(img: np.ndarray, wall_target: float, lift: float, denoise: int, warmth: float) -> tuple[np.ndarray, dict]:
    f = img.astype(np.float32) / 255.0
    wall = estimate_backdrop(img)
    # 1. white balance: scale channels so the backdrop becomes neutral grey of the same luminance
    lum = wall.mean()
    gains = lum / np.maximum(wall, 1e-3)
    gains = gains / gains.mean()
    if warmth:  # optional gentle warm bias like daylight salon photos
        gains = gains * np.array([1 + warmth, 1.0, 1 - warmth], np.float32)
    f = np.clip(f * gains, 0, 1)
    # 2. exposure: linear gain so the backdrop lands at wall_target (like +EV), blended by `lift`,
    #    with a smooth highlight shoulder above `knee` so nothing clips flat
    cur = float(np.clip(lum, 0.05, 0.98))
    gain = 1 + (wall_target / cur - 1) * lift
    f = f * gain
    knee = 0.80
    hi = f > knee
    f = np.where(hi, knee + (1 - knee) * (1 - np.exp(-(f - knee) / (1 - knee))), f)
    out = (np.clip(f, 0, 1) * 255).astype(np.uint8)
    # 3. denoise + light sharpen
    if denoise > 0:
        bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
        bgr = cv2.fastNlMeansDenoisingColored(bgr, None, denoise, denoise, 7, 21)
        out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    blur = cv2.GaussianBlur(out, (0, 0), 2.0)
    out = cv2.addWeighted(out, 1.25, blur, -0.25, 0)
    info = {"backdrop_before": [round(float(v), 3) for v in wall], "wb_gains": [round(float(g), 3) for g in gains],
            "gain": round(float(gain), 3), "backdrop_after": [round(float(v), 3) for v in estimate_backdrop(out)]}
    return out, info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--wall-target", type=float, default=0.93)
    ap.add_argument("--lift", type=float, default=1.0, help="0 = no exposure change, 1 = full correction to wall target")
    ap.add_argument("--denoise", type=int, default=5, help="fastNlMeans strength, 0 = off")
    ap.add_argument("--warmth", type=float, default=0.0, help="e.g. 0.02 for a slightly warm daylight bias")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for p in a.images:
        img = cv2.cvtColor(cv2.imread(str(p), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        if img is None:
            sys.exit(f"cannot read {p}")
        out, info = process(img, a.wall_target, a.lift, a.denoise, a.warmth)
        dst = a.out / p.name
        cv2.imwrite(str(dst), cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{p.name}: {info} -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
