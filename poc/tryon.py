#!/usr/bin/env python3
"""Nail try-on PoC, slice 1: hand photo + reference photo -> N candidates via Nano Banana Pro.

Usage:
  python poc/tryon.py --hand hands/cup.jpg --ref refs/hb-3.jpg [--n 3] [--size 2K] [--adopt-shape]
                      [--notes "..."] [--out-root ~/nail-tryon-data/runs] [--dry-run]

The API key is read from $GEMINI_API_KEY, else from ~/.config/nail-tryon/.env
(a line `GEMINI_API_KEY=...`). Missing key -> hard error, nothing is faked.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompts  # noqa: E402

MODEL = "gemini-3-pro-image-preview"
KEY_FILE = Path.home() / ".config" / "nail-tryon" / ".env"
# Third-party quotes of the Gemini API price list (not verified on ai.google.dev):
# ~$0.134 per 1K/2K output image, ~$0.24 per 4K image, $2 per 1M input tokens.
PRICE_PER_IMAGE = {"1K": 0.134, "2K": 0.134, "4K": 0.24}
PRICE_INPUT_PER_M = 2.0
ASPECTS = {"1:1": 1.0, "4:5": 0.8, "5:4": 1.25, "3:4": 0.75, "4:3": 4 / 3, "2:3": 2 / 3,
           "3:2": 1.5, "9:16": 9 / 16, "16:9": 16 / 9, "21:9": 21 / 9}
MAX_HAND_SIDE = 2048
MAX_REF_SIDE = 1536


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit(
            "GEMINI_API_KEY not found. Export it or put a line `GEMINI_API_KEY=...` in "
            f"{KEY_FILE} (chmod 600). Create a key at https://aistudio.google.com/apikey ."
        )
    return key


def prep_image(path: Path, max_side: int) -> tuple[bytes, Image.Image]:
    img = Image.open(path)
    img = img.convert("RGB")
    # honour EXIF orientation so the model sees the photo upright
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img)
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), img


def nearest_aspect(w: int, h: int) -> str:
    r = w / h
    return min(ASPECTS, key=lambda k: abs(ASPECTS[k] - r))


def write_report(run: Path, meta: dict) -> None:
    cands = "".join(
        f'<figure><img src="{c["file"]}" loading="lazy"><figcaption>{c["file"]} · '
        f'{c.get("elapsed_s", "?")}s{" · " + c["note"] if c.get("note") else ""}</figcaption></figure>'
        for c in meta["candidates"]
    )
    html = f"""<!doctype html><meta charset="utf-8"><title>{run.name}</title>
<style>
body{{font:14px/1.4 -apple-system,system-ui,sans-serif;margin:16px;background:#111;color:#ddd}}
.row{{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}}
figure{{margin:0;max-width:560px}} img{{width:100%;height:auto;display:block;border-radius:6px;background:#000}}
figcaption{{font-size:12px;color:#999;margin-top:4px}} pre{{white-space:pre-wrap;background:#1b1b1b;padding:10px;border-radius:6px}}
h2{{font-size:15px;margin:22px 0 8px}}
</style>
<h2>Inputs</h2>
<div class="row">
<figure><img src="input-hand.jpg"><figcaption>Image 1 · hand · {meta["hand"]["sent_size"]}</figcaption></figure>
<figure><img src="input-ref.jpg"><figcaption>Image 2 · reference · {meta["ref"]["sent_size"]}</figcaption></figure>
</div>
<h2>Candidates ({len(meta["candidates"])})</h2>
<div class="row">{cands or "<p>none (dry run or all calls failed)</p>"}</div>
<h2>Run</h2>
<pre>model {meta["model"]} · size {meta["image_size"]} · aspect {meta["aspect_ratio"]} · prompt {meta["prompt_version"]}
estimated cost ${meta["estimated_cost_usd"]:.3f} (price list quoted from third parties)
{json.dumps(meta.get("usage", {}), indent=1)}</pre>
<h2>Prompt</h2><pre>{meta["prompt"]}</pre>
"""
    (run / "report.html").write_text(html, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hand", required=True, type=Path)
    ap.add_argument("--ref", required=True, type=Path)
    ap.add_argument("--n", type=int, default=3, help="candidates to generate (sequential calls)")
    ap.add_argument("--size", choices=["1K", "2K", "4K"], default="2K")
    ap.add_argument("--adopt-shape", action="store_true", help="take nail length/shape from the reference")
    ap.add_argument("--notes", default="", help="extra instructions appended to the prompt")
    ap.add_argument("--out-root", type=Path, default=Path.home() / "nail-tryon-data" / "runs")
    ap.add_argument("--dry-run", action="store_true", help="validate inputs, write prompt + report, no API call")
    a = ap.parse_args()

    for p in (a.hand, a.ref):
        if not p.is_file():
            sys.exit(f"input not found: {p}")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run = a.out_root / f"{stamp}-{a.hand.stem}-{a.ref.stem}"
    run.mkdir(parents=True, exist_ok=False)

    hand_bytes, hand_img = prep_image(a.hand, MAX_HAND_SIDE)
    ref_bytes, ref_img = prep_image(a.ref, MAX_REF_SIDE)
    (run / "input-hand.jpg").write_bytes(hand_bytes)
    (run / "input-ref.jpg").write_bytes(ref_bytes)
    aspect = nearest_aspect(*hand_img.size)
    prompt = prompts.build(adopt_shape=a.adopt_shape, notes=a.notes)

    meta = {
        "model": MODEL, "image_size": a.size, "aspect_ratio": aspect,
        "prompt_version": prompts.PROMPT_VERSION, "prompt": prompt,
        "adopt_shape": a.adopt_shape, "notes": a.notes,
        "hand": {"source": str(a.hand.resolve()), "sent_size": f"{hand_img.size[0]}x{hand_img.size[1]}"},
        "ref": {"source": str(a.ref.resolve()), "sent_size": f"{ref_img.size[0]}x{ref_img.size[1]}"},
        "requested": a.n, "candidates": [], "usage": {"input_tokens": 0, "output_tokens": 0},
        "estimated_cost_usd": 0.0, "errors": [],
    }

    if a.dry_run:
        meta["estimated_cost_usd"] = a.n * PRICE_PER_IMAGE[a.size]
        (run / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        write_report(run, meta)
        print(f"dry run: {run}/report.html  (would cost ≈ ${meta['estimated_cost_usd']:.2f} for {a.n} × {a.size})")
        return 0

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=load_key())
    contents = [
        prompt,
        types.Part.from_bytes(data=hand_bytes, mime_type="image/jpeg"),
        types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg"),
    ]
    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect, image_size=a.size),
    )

    for i in range(1, a.n + 1):
        t0 = time.time()
        try:
            resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
        except Exception as e:  # fail loud, keep going so one bad call doesn't lose the run
            msg = f"candidate {i}: API error: {type(e).__name__}: {e}"
            print(msg, file=sys.stderr)
            meta["errors"].append(msg)
            continue
        elapsed = round(time.time() - t0, 1)
        um = getattr(resp, "usage_metadata", None)
        if um:
            meta["usage"]["input_tokens"] += um.prompt_token_count or 0
            meta["usage"]["output_tokens"] += um.candidates_token_count or 0
        saved = False
        notes = []
        for part in (resp.candidates[0].content.parts if resp.candidates else []):
            if part.inline_data and part.inline_data.data:
                ext = "png" if "png" in (part.inline_data.mime_type or "") else "jpg"
                fn = f"cand-{i}.{ext}"
                (run / fn).write_bytes(part.inline_data.data)
                meta["candidates"].append({"file": fn, "elapsed_s": elapsed, "note": " ".join(notes)})
                meta["estimated_cost_usd"] += PRICE_PER_IMAGE[a.size]
                saved = True
                print(f"candidate {i}: {fn} in {elapsed}s")
            elif part.text:
                notes.append(part.text.strip())
        if not saved:
            fr = getattr(resp.candidates[0], "finish_reason", None) if resp.candidates else None
            msg = f"candidate {i}: no image returned (finish_reason={fr}; text={' '.join(notes)[:300]!r})"
            print(msg, file=sys.stderr)
            meta["errors"].append(msg)

    meta["estimated_cost_usd"] += meta["usage"]["input_tokens"] / 1e6 * PRICE_INPUT_PER_M
    (run / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    write_report(run, meta)
    print(f"report: {run}/report.html  · {len(meta['candidates'])}/{a.n} images · ≈ ${meta['estimated_cost_usd']:.3f}")
    return 0 if meta["candidates"] else 1


if __name__ == "__main__":
    sys.exit(main())
