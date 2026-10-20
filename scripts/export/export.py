from ultralytics import YOLO
import json, os, shutil
# This is the only pickle load. The container has no network, credentials, repository or Docker socket.
shutil.copyfile('/input/model.pt', '/tmp/nails.pt')
model = YOLO('/tmp/nails.pt')
model.export(format='onnx', imgsz=640, opset=12, simplify=True, dynamic=False, batch=1, device='cpu', half=False)
shutil.copyfile('/tmp/nails.onnx', '/output/nails-fp32.onnx')
with open('/output/export-info.json', 'w') as f:
    json.dump({'names': model.names, 'task': model.task, 'export': {'imgsz':640,'opset':12,'simplify':True,'dynamic':False}}, f, indent=2)
