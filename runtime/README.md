# ONNX Runtime Web 1.19.2

Vendored from `https://cdn.jsdelivr.net/npm/onnxruntime-web@1.19.2/dist/` so the static site does not depend on an external CDN at runtime. MIT license: [LICENSE](LICENSE).

| File | SHA-256 |
| --- | --- |
| ort.wasm.min.js | 98e831517582c08fc1b729def487a8b0152c83fc641746137eb4c7ad46032f1c |
| ort-wasm-simd-threaded.mjs | d870a377322c3053fb97432d548423f165dd15e2af232947592fc07b0d2f3639 |
| ort-wasm-simd-threaded.wasm | 1bf0b9ed7ad025cf9ca88ce6da29e54df3f128a169f8241d71823e81f078d578 |

The threaded-capable artifact also runs with `numThreads=1`; the app sets this explicitly so SharedArrayBuffer / cross-origin isolation are not needed on GitHub Pages.
