# PoC · 客图上手（Nano Banana Pro）

目标：顾客手照 + 一张客图（小红书等来源的款式照）→ 几张把该款式真实渲染到顾客手上的候选图。
这是第 1 片：直接两图输入、多候选出图、生成对比报告。逐指提取、合成守门等按验证结果再加。

## 运行

```sh
cd poc && uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install google-genai pillow numpy
python tryon.py --hand ~/nail-tryon-data/hands/cup.jpg --ref ~/nail-tryon-data/refs/hb-3.jpg --n 3
open ~/nail-tryon-data/runs/<run>/report.html
```

- `--size 1K|2K|4K`（默认 2K）、`--adopt-shape`（甲型长度跟客图，默认保留顾客自己的）、`--notes "..."`（美甲师补充要求）、`--dry-run`（不调接口，只写提示词和报告，顺便估价）。
- 每次运行在 `~/nail-tryon-data/runs/<时间戳-手照-客图>/` 下留下输入副本、候选图、`meta.json`（模型、尺寸、提示词版本、token 用量、估算费用、错误）和 `report.html`。
- 测试图片放在仓库外的 `~/nail-tryon-data/`，客图来自公开文章，有版权，不进 git。

## 密钥

读 `$GEMINI_API_KEY`，否则读 `~/.config/nail-tryon/.env` 里的 `GEMINI_API_KEY=...`。没有就直接报错退出，不会伪造输出。
在 https://aistudio.google.com/apikey 创建，需绑定已开通计费的 Google Cloud 项目（Nano Banana Pro 只在付费档提供）。

## 价格

第三方转述的官方价目：1K/2K 每张约 $0.134，4K 约 $0.24，输入每百万 token $2。`meta.json` 里的 `estimated_cost_usd` 按此估算，未在官方页核对。
