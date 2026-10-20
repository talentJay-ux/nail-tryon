FROM python:3.11-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN --mount=type=secret,id=system_ca,required=true PIP_CERT=/run/secrets/system_ca pip install --no-cache-dir torch==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=secret,id=system_ca,required=true PIP_CERT=/run/secrets/system_ca pip install --no-cache-dir torch==2.7.1+cpu torchvision==0.22.1+cpu ultralytics-thop==2.0.18 ultralytics==8.3.221 onnx==1.17.0 onnxslim==0.1.71 onnxruntime==1.19.2
ENV YOLO_CONFIG_DIR=/tmp/ultralytics OMP_NUM_THREADS=4
RUN --mount=type=secret,id=system_ca,required=true pip uninstall -y opencv-python && PIP_CERT=/run/secrets/system_ca pip install --no-cache-dir opencv-python-headless==4.11.0.86
ENV YOLO_AUTOINSTALL=false
