"""Compress exported ONNX only. Never opens the pickle checkpoint or trains weights."""
import argparse
from pathlib import Path
import numpy as np
import onnx
from onnx import helper, numpy_helper, TensorProto
from onnxruntime.quantization import quantize_dynamic, QuantType


def compress(source, output):
    output.mkdir(parents=True, exist_ok=True)
    model=onnx.load(source)
    # Store FP16 weights with explicit FP32 Casts: also works in WASM backends
    # that do not implement native half-precision Conv kernels.
    casts=[]
    for init in model.graph.initializer:
        if init.data_type!=TensorProto.FLOAT:continue
        original=init.name
        init.CopyFrom(numpy_helper.from_array(numpy_helper.to_array(init).astype(np.float16),original+'_fp16'))
        casts.append(helper.make_node('Cast',[init.name],[original],name=original+'_to_float',to=TensorProto.FLOAT))
    nodes=list(model.graph.node);del model.graph.node[:];model.graph.node.extend(casts+nodes)
    onnx.checker.check_model(model)
    onnx.save(model, output/'nails-fp16.onnx')
    quantize_dynamic(str(source), str(output/'nails-dynamic-int8.onnx'), weight_type=QuantType.QUInt8,
                     per_channel=False, op_types_to_quantize=['Conv','MatMul'])
    # Portable weight-only INT8: weights are stored as signed bytes; DQ restores
    # them for float Conv, avoiding unsupported/low-accuracy ConvInteger kernels.
    # Per-output-channel scaling preserves the segmentation head's small weights.
    model=onnx.load(source)
    initializers={i.name:i for i in model.graph.initializer}
    quantized=set(); nodes=[]; additions=[]
    for node in model.graph.node:
        if node.op_type=='Conv' and node.input[1] in initializers:
            name=node.input[1]
            if name not in quantized:
                weight=numpy_helper.to_array(initializers[name]); axes=tuple(range(1,weight.ndim))
                scale=np.maximum(np.max(np.abs(weight),axis=axes)/127,1e-12).astype(np.float32)
                q=np.clip(np.rint(weight/scale.reshape((-1,)+(1,)*(weight.ndim-1))),-127,127).astype(np.int8)
                additions.extend([numpy_helper.from_array(q,name+'_int8'),numpy_helper.from_array(scale,name+'_scale'),
                                  numpy_helper.from_array(np.zeros(len(scale),dtype=np.int8),name+'_zero')])
                nodes.append(helper.make_node('DequantizeLinear',[name+'_int8',name+'_scale',name+'_zero'],[name+'_float'],name=name+'_DQ',axis=0))
                quantized.add(name)
            node.input[1]=name+'_float'
        nodes.append(node)
    remaining=[i for i in model.graph.initializer if i.name not in quantized]
    del model.graph.node[:];model.graph.node.extend(nodes)
    del model.graph.initializer[:];model.graph.initializer.extend(remaining+additions)
    # Per-axis DequantizeLinear was introduced in opset 13; the source export is 12.
    # Explicitly convert the graph (not just relabel the opset): Split/Unsqueeze/etc change schema.
    model=onnx.version_converter.convert_version(model,13)
    model.doc_string='mnemic/nails_seg_yolov8 CC-BY-4.0; per-output-channel INT8 weights, FP32 activations.'
    onnx.checker.check_model(model)
    onnx.save(model,output/'nails-weight-int8.onnx')
    for p in sorted(output.glob('*.onnx')):print(f'{p.name}: {p.stat().st_size:,} bytes')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();compress(a.source,a.output)
