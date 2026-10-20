# 美甲试色镜

上传照片，按真实指甲轮廓试色。保留 88 个编号色号、图案、质感、点缀、单指编辑、甲型、可选延长、拖动及宽窄／长短／角度修正、效果图和设计单文字导出。手机仍使用单屏底部半透明面板。

在线试用：https://talentjay-ux.github.io/nail-tryon/

## 如何定位和渲染

- YOLOv8s-seg 在浏览器 Worker 中通过 **onnxruntime-web 1.19.2 / WASM** 运行。照片不上传；运行库、WASM 和 ONNX 都从本站加载，无 CDN 依赖。无需后端或训练。
- 输入为 RGB、`float32 [1,3,640,640]`，等比例缩放并以 114 补边。JS 对 `output0 [1,37,8400]` 做置信度过滤和 IoU 0.45 的 NMS；32 个 mask 系数与 `output1 [1,32,160,160]` 原型相乘、sigmoid、框内裁剪、去补边，再映射回照片。
- 先上采样概率，再阈值化和轻微羽化，每片甲使用独立蒙版。底色、图案、质感和点缀都在 `x∈[-0.5,0.5]、y∈[0,1]` 的单位坐标内绘制，随蒙版的 PCA 长轴旋转，最后按真实蒙版裁剪。羽化使用像素 alpha，不依赖 Safari 较旧版本缺少的 `Canvas.filter`。
- MediaPipe Hands **只用于**最近 TIP 的手指归属及 DIP→TIP 的方向判断，不再生成指甲矩形。无匹配时仍渲染，采用“全部”的独立设置，方向取远离所有指甲质心的一端；只有一片时采用朝上的确定性方向。
- 默认“真实轮廓、不延长”。四种甲型模板用于轮廓内塑形；延长将实际轮廓沿长轴拉伸，固定甲根。手动拖动、宽窄、长短、角度同时变换图案和蒙版。新照片清空位置修正，保留配色设置。
- “位置”页可调识别门槛（0.10～0.70），直接重解码已缓存输出，不重复运行模型。点选未匹配手指的甲片仍能单独修正位置，其设计始终使用“全部”。设计单会注明这些甲片。

## 模型、体积和许可

**Model: [mnemic/nails_seg_yolov8](https://huggingface.co/mnemic/nails_seg_yolov8) (CC-BY-4.0)**。
许可：[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)。原作者发布的模型经 ONNX 导出及量化，未重新训练。详细来源及校验值见 [models/ATTRIBUTION.md](models/ATTRIBUTION.md)。

| 候选 | 字节数 | 结果 |
| --- | ---: | --- |
| FP32，640，opset 12，simplify | 47,375,205 | 精度对比基线 |
| FP16 权重存储、FP32 运算 | 23,749,925 | 超过 15 MB |
| **动态 INT8（U8 权重 / U8 激活）** | **12,374,423（12.37 MB / 11.80 MiB）** | **已发布，保留 opset 12** |
| 每通道 INT8 权重、FP32 激活 | 12,328,696 | 备选，需 opset 13；未发布 |

动态量化使用 ONNX Runtime 1.19.2 `quantize_dynamic`，`weight_type=QUInt8`、`per_channel=False`，作用于 Conv / MatMul。五张公开测试图的检出数量与 FP32 相同，逐图平均 mask IoU 为 **95.8%～99.4%**。这是对 FP32 的一致性检查，**不是人工标注准确率**，也不代表完整数据集精度。

[完整验证报告、改前／改后截图及模型压缩对照](docs/validation/README.md)。

## 加载与浏览器

页面本身立即可用，选图后才加载模型。首次获得试色需要约 **23.5 MB**（模型 12.37 MB + WASM 11.02 MB + JS/MJS）；模型通过带版本的 Cache Storage 缓存并校验 SHA-256，缓存不可用时仍可运行。手指归属模型在试色出现后再加载，额外约 16.2 MB，不阻塞试色。

在桌面主机上，Chromium 与 Playwright WebKit 的 iPhone 13 尺寸模拟均已运行真实 ONNX，完成交互和导出测试。模拟 10 Mbps 下载、80 ms 延迟、空缓存时，约 **22 秒**出现试色，约 38 秒完成可选手指归属。真实网络、手机算力和 Safari 的内存限制会改变耗时；**本次未使用真实 iPhone 验收**。需要 HTTPS（本地开发可用 localhost）、Worker 和 WebAssembly SIMD；Pages 无需配置 COOP/COEP，推理固定单线程。

## 已知局限

- **仍会漏检**：双手叠放的花纹甲样例检出 6/9 片；降低门槛到 0.10 可恢复其中一片，另两片仍漏检。侧面只露很薄甲缘、反光强、严重遮挡、模糊或在整图中很小的指甲尤其困难。分割无法恢复被遮住的甲面。
- 部分边界仍会少涂或多涂少量皮肤，尤其侧向拇指、透明甲尖、复杂花纹和长尖甲。可用已有位置修正调整已检测甲片；调整门槛不能保证找回完全漏掉的甲片。
- MediaPipe 没找到手时，指甲仍可试色，但不能可靠区分拇指至小指；按“全部”设置绘制。交叉、透视或超长甲可能使最近 TIP 匹配错误，单指设计需核对。
- 无关键点时的甲尖方向是启发式；双手相向、单片甲或接近圆形的甲面可能反向，需要手动调角度。延长及模板是二维预览，不会生成新的手部遮挡关系。
- 首次下载较大，旧手机可能较慢；浏览器可能清理模型缓存。照片处理最长边限制为 1600 px，模型输入固定 640 px。

## 开发和复现

网页仍是 `index.html` 内联 CSS / JS + Canvas 2D。无需构建即可静态托管；`runtime/` 锁定 ORT 1.19.2，`mp/` 保留原 MediaPipe 文件。

```sh
npm ci
npm test
python3 -m http.server 8080
# 在另一个终端运行，需要 Playwright Chromium：
npm run test:browser
# WebKit：npx playwright install --with-deps webkit
BROWSER=webkit npm run test:browser
```

测试可用 `BASE_URL`、`CHROMIUM_EXECUTABLE`、`WEBKIT_EXECUTABLE` 指定环境。共享后处理源码在 `scripts/postprocess.js`，修改后运行 `npm run build` 同步回单页；测试会检查二者一致。

`.pt` 使用 pickle，**不要在日常工作环境直接加载**。本次只在无网络、非 root、只读根文件系统、去权限的 Docker 容器内加载一次，容器只挂载输入权重和导出目录，不接触仓库、凭据或 Docker socket。导出前已固定来源提交和 SHA-256。

```sh
python3 -m pip install onnx==1.17.0 onnxruntime==1.19.2 numpy opencv-python-headless==4.11.0.86
# Docker 构建下载依赖；真正加载 .pt 的容器使用 --network none。
bash scripts/export-model.sh
# ONNX 比较与压缩只处理 ONNX，不再加载 .pt：
python3 scripts/compare-models.py model-build/output/nails-fp32.onnx model-build/compressed tests/fixtures model-build/evaluation
```

部署时将相同提交推到 `main` 和 `gh-pages`；GitHub Pages 保持从 `gh-pages:/` 发布。
