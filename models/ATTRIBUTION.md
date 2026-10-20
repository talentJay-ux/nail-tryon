# Model attribution

Model: [mnemic/nails_seg_yolov8](https://huggingface.co/mnemic/nails_seg_yolov8) (CC-BY-4.0).

- Author / publisher: mnemic (MNeMoNiCuZ).
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
- Original: `nails_seg_s_yolov8_v1.pt`, single-class `nail`, YOLOv8s-seg.
- Hugging Face revision: `187ebf22c110e38d4f9f60ff2b04b29629cff11c`.
- Original SHA-256: `99b7d1c6ceb4bde32d80fe7ae8c8eb809c27d99b55cf9db54b6692afe68f4070`.
- Changes: Ultralytics 8.3.221 ONNX export (640, opset 12, simplify, batch 1, static shape), then ONNX Runtime 1.19.2 dynamic 8-bit quantization (QUInt8 weights, dynamic uint8 activations; Conv / MatMul; per-tensor). No training or calibration dataset.
- Deployed file: `nails-int8.onnx`, 12,374,423 bytes.
- Deployed SHA-256: `27ad00b46b2a57c3011dfda0bd325b88c4358d47a7a6d92d55cfe1e24f15f60b`.

The original model card identifies [Personal Projects / Nails Segmentation](https://universe.roboflow.com/personal-projects-jfbag/nails_segmentation) as its training data. This project uses the published checkpoint; it does not train on the evaluation photos.
