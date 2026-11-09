#!/usr/bin/env python3
"""Slice 2, stage 1: turn a reference nail photo into an explicit per-finger design spec (JSON).

  python poc/extract.py --ref style.jpg --out spec.json [--model gemini-3.8-flash]

The spec is what the nail technician reviews/edits and what tryon.py --spec injects into the
image prompt, so the image model is told the colour, opacity and finish instead of guessing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tryon import load_key, prep_image, MAX_REF_SIDE  # noqa: E402

DEFAULT_MODEL = "gemini-3.8-flash"

SCHEMA = {
    "type": "object",
    "properties": {
        "overall": {
            "type": "object",
            "properties": {
                "nail_shape": {"type": "string", "description": "square | squoval | round | oval | almond | coffin | stiletto"},
                "nail_length": {"type": "string", "description": "short | medium | long | extra-long, judged against the fingertip"},
                "opacity": {"type": "string", "description": "opaque | semi-sheer | sheer. opaque = nail plate and free edge are NOT visible through the polish"},
                "free_edge_visible": {"type": "boolean", "description": "true only if a lighter/whiter nail tip shows through the polish"},
                "base_color_hex": {"type": "string", "description": "sRGB hex of the polish body colour in a mid-tone area, away from highlights and shadows"},
                "base_color_name": {"type": "string", "description": "plain-language colour name, e.g. dusty mauve pink, milky nude, grey-blue"},
                "finish": {"type": "string", "description": "glossy cream | jelly/glazed | cat-eye | chrome/mirror | pearl | matte | glitter | shimmer"},
                "sheen": {"type": "string", "description": "none | subtle pearl | strong pearl | magnetic cat-eye streak | metallic"},
                "art_summary": {"type": "string", "description": "one sentence: patterns, French tips, foil, charms, gems, or 'none'"},
            },
            "required": ["nail_shape", "nail_length", "opacity", "free_edge_visible", "base_color_hex", "base_color_name", "finish", "sheen", "art_summary"],
        },
        "fingers": {
            "type": "array",
            "description": "one entry per visible nail; use 'unknown' for finger if it cannot be told",
            "items": {
                "type": "object",
                "properties": {
                    "finger": {"type": "string", "description": "thumb | index | middle | ring | pinky | unknown"},
                    "same_as_overall": {"type": "boolean"},
                    "design": {"type": "string", "description": "what differs from overall, or 'same'"},
                },
                "required": ["finger", "same_as_overall", "design"],
            },
        },
        "render_notes": {"type": "string", "description": "2-3 sentences a painter would need to reproduce this exactly: coverage, tip treatment, highlight character"},
    },
    "required": ["overall", "fingers", "render_notes"],
}

PROMPT = """You are a senior nail technician writing a work order from a client's reference photo.
Describe ONLY the nail polish/design in this photo, precisely enough that another technician could reproduce it without seeing the photo.
Be literal: judge opacity by whether the natural nail plate or a lighter free edge shows through. Estimate the body colour as an sRGB hex from a mid-tone area of a nail, not from a highlight.
If all nails share one design, say so and still list each visible nail."""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    if not a.ref.is_file():
        sys.exit(f"reference not found: {a.ref}")

    from google import genai
    from google.genai import types

    ref_bytes, _ = prep_image(a.ref, MAX_REF_SIDE)
    client = genai.Client(api_key=load_key())
    resp = client.models.generate_content(
        model=a.model,
        contents=[PROMPT, types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=SCHEMA, temperature=0.2),
    )
    text = resp.text
    if not text:
        sys.exit(f"no text returned: finish_reason={resp.candidates[0].finish_reason if resp.candidates else None}")
    spec = json.loads(text)
    spec["_meta"] = {"model": a.model, "reference": str(a.ref.resolve()),
                     "usage": {"input_tokens": resp.usage_metadata.prompt_token_count, "output_tokens": resp.usage_metadata.candidates_token_count}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    print(json.dumps(spec, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
