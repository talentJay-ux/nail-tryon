#!/usr/bin/env python3
"""Stage 0: re-render a dim/noisy customer hand photo in the bright, clean photographic style of the
reference photo, changing nothing about the hand itself. Output feeds tryon.py as the hand photo.

  python poc/relight.py --hand IMG --ref IMG --out-root DIR [--n 2] [--size 2K]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tryon import MODEL, PRICE_PER_IMAGE, load_key, nearest_aspect, prep_image, MAX_HAND_SIDE, MAX_REF_SIDE  # noqa: E402

PROMPT_VERSION = "relight-v1"
PROMPT = """\
Image 1 is a customer's hand photographed indoors in dim, slightly cool, noisy light. Image 2 is a reference for PHOTOGRAPHIC STYLE ONLY (lighting, exposure, clarity, cleanliness).

Re-render Image 1 as if it had been photographed under the same conditions as Image 2: bright, soft, even daylight; clean near-white neutral backdrop; bright, evenly lit skin with natural warm tone; crisp, sharp focus with fine skin texture; no noise, grain or haze; natural, slightly airy high-key look.

Keep absolutely everything else identical to Image 1: the same hand, pose, finger positions and proportions, nail shapes and lengths, the gold bangle, framing and camera angle, wall and floor layout. Do not copy any object, ring, nail design or polish from Image 2. Do not add or change nail polish: the nails stay exactly as they are in Image 1, only better lit.
Output only the re-lit photograph. No text, no watermark, no collage.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hand", required=True, type=Path)
    ap.add_argument("--ref", required=True, type=Path)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--size", choices=["1K", "2K", "4K"], default="2K")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--out-root", type=Path, default=Path.home() / "nail-tryon-data" / "runs" / "relight")
    a = ap.parse_args()

    from google import genai
    from google.genai import types

    hand_bytes, hand_img = prep_image(a.hand, MAX_HAND_SIDE)
    ref_bytes, _ = prep_image(a.ref, MAX_REF_SIDE)
    run = a.out_root / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{a.hand.stem}"
    run.mkdir(parents=True)
    (run / "input-hand.jpg").write_bytes(hand_bytes)
    (run / "input-ref.jpg").write_bytes(ref_bytes)
    aspect = nearest_aspect(*hand_img.size)
    client = genai.Client(api_key=load_key())
    config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"],
                                         image_config=types.ImageConfig(aspect_ratio=aspect, image_size=a.size))
    contents = [PROMPT, types.Part.from_bytes(data=hand_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")]
    meta = {"model": a.model, "image_size": a.size, "aspect_ratio": aspect, "prompt_version": PROMPT_VERSION,
            "prompt": PROMPT, "hand": str(a.hand.resolve()), "ref": str(a.ref.resolve()), "candidates": [], "errors": [],
            "estimated_cost_usd": 0.0}
    for i in range(1, a.n + 1):
        t0 = time.time()
        try:
            resp = client.models.generate_content(model=a.model, contents=contents, config=config)
        except Exception as e:
            meta["errors"].append(f"candidate {i}: {type(e).__name__}: {e}"); print(meta["errors"][-1][:300], file=sys.stderr); continue
        cand0 = resp.candidates[0] if resp.candidates else None
        parts = cand0.content.parts if (cand0 and cand0.content and cand0.content.parts) else []
        saved = False
        for part in parts:
            if part.inline_data and part.inline_data.data:
                fn = f"relit-{i}.jpg"; (run / fn).write_bytes(part.inline_data.data)
                meta["candidates"].append({"file": fn, "elapsed_s": round(time.time() - t0, 1)})
                meta["estimated_cost_usd"] += PRICE_PER_IMAGE[a.size]; saved = True
                print(f"candidate {i}: {fn} in {round(time.time() - t0, 1)}s")
        if not saved:
            meta["errors"].append(f"candidate {i}: no image (finish_reason={getattr(cand0, 'finish_reason', None)})")
            print(meta["errors"][-1], file=sys.stderr)
    (run / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"run: {run} · {len(meta['candidates'])}/{a.n} · ≈ ${meta['estimated_cost_usd']:.2f}")
    return 0 if meta["candidates"] else 1


if __name__ == "__main__":
    sys.exit(main())
