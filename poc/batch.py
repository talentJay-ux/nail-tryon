#!/usr/bin/env python3
"""Run tryon.py over every hand × reference pair and build one review grid.

  python poc/batch.py [--hands DIR] [--refs DIR] [--n 3] [--size 2K] [--model ID] [-- extra tryon args]

Output: ~/nail-tryon-data/runs/batch-<stamp>/index.html (rows = hands, columns = references,
cells = candidates; every image links to that pair's report.html).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMG = {".jpg", ".jpeg", ".png", ".webp"}


def build_index(batch: Path, hands: list[Path], refs: list[Path], results: list[dict]) -> Path:
    by = {(r["hand"], r["ref"]): r for r in results}
    n_img = sum(len(r["meta"].get("candidates", [])) for r in results)
    cost = sum(r["meta"].get("estimated_cost_usd", 0) for r in results)
    errs = sum(len(r["meta"].get("errors", [])) for r in results)

    def thumb(run: Path | None, name: str) -> str:
        return f'<img src="{run.name}/{name}">' if run else ""

    head = "".join(
        f"<th>{r.name}<br>{thumb(next((x['run'] for x in results if x['ref'] == r.name and x['run']), None), 'input-ref.jpg')}</th>"
        for r in refs
    )
    rows = []
    for h in hands:
        first = next((x["run"] for x in results if x["hand"] == h.name and x["run"]), None)
        cells = []
        for r in refs:
            x = by.get((h.name, r.name))
            if not x or not x["run"]:
                cells.append("<td class=err>no run</td>")
                continue
            cands = "".join(
                f'<a href="{x["run"].name}/report.html"><img src="{x["run"].name}/{c["file"]}"></a>'
                for c in x["meta"].get("candidates", [])
            )
            e = len(x["meta"].get("errors", []))
            cells.append(f"<td>{cands or '<span class=err>no image</span>'}{f'<div class=err>{e} error(s)</div>' if e else ''}</td>")
        rows.append(f"<tr><th>{h.name}<br>{thumb(first, 'input-hand.jpg')}</th>{''.join(cells)}</tr>")

    model = next((x["meta"].get("model") for x in results if x["meta"]), "?")
    size = next((x["meta"].get("image_size") for x in results if x["meta"]), "?")
    pv = next((x["meta"].get("prompt_version") for x in results if x["meta"]), "?")
    html = f"""<!doctype html><meta charset="utf-8"><title>{batch.name}</title>
<style>
body{{font:13px/1.4 -apple-system,system-ui,sans-serif;margin:16px;background:#111;color:#ddd}}
table{{border-collapse:collapse}} th,td{{border:1px solid #333;padding:6px;vertical-align:top;text-align:left}}
th img{{width:150px;display:block;margin-top:4px;border-radius:4px}}
td img{{width:230px;display:block;margin-bottom:6px;border-radius:4px}} td a:hover img{{outline:2px solid #6cf}}
.err{{color:#f66}} p{{color:#aaa}}
</style>
<h2>{batch.name}</h2>
<p>model {model} · size {size} · prompt {pv} · {n_img} images · ≈ ${cost:.2f} · {errs} errors · click an image for its report</p>
<table><tr><th>hand \\ reference</th>{head}</tr>{''.join(rows)}</table>
"""
    out = batch / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hands", type=Path, default=Path.home() / "nail-tryon-data" / "hands")
    ap.add_argument("--refs", type=Path, default=Path.home() / "nail-tryon-data" / "refs")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--size", default="2K")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out-root", type=Path, default=Path.home() / "nail-tryon-data" / "runs")
    ap.add_argument("extra", nargs="*", help="extra args for tryon.py, after `--`")
    a = ap.parse_args()

    hands = sorted(p for p in a.hands.iterdir() if p.suffix.lower() in IMG)
    refs = sorted(p for p in a.refs.iterdir() if p.suffix.lower() in IMG)
    if not hands or not refs:
        sys.exit(f"no images: hands={len(hands)} refs={len(refs)}")
    batch = a.out_root / f"batch-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    batch.mkdir(parents=True)
    print(f"{len(hands)} hands × {len(refs)} refs × {a.n} → {batch}", flush=True)

    results = []
    for h in hands:
        for r in refs:
            cmd = [sys.executable, str(HERE / "tryon.py"), "--hand", str(h), "--ref", str(r),
                   "--n", str(a.n), "--size", a.size, "--out-root", str(batch)]
            if a.model:
                cmd += ["--model", a.model]
            cmd += a.extra
            print(f">> {h.name} × {r.name}", flush=True)
            rc = subprocess.run(cmd).returncode
            runs = sorted(batch.glob(f"*-{h.stem}-{r.stem}"))
            run = runs[-1] if runs else None
            meta = json.loads((run / "meta.json").read_text()) if run and (run / "meta.json").exists() else {}
            results.append({"hand": h.name, "ref": r.name, "run": run, "meta": meta, "rc": rc})
            build_index(batch, hands, refs, results)  # keep the grid current while the batch runs
    out = build_index(batch, hands, refs, results)
    print(f"grid: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
