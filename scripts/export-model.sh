#!/usr/bin/env bash
# Reproduce the one-time isolated export. No training; never load .pt on the host.
set -euo pipefail
nail_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
nail_build="${1:-$nail_root/model-build}"
mkdir -p "$nail_build/output"
curl -fL 'https://huggingface.co/mnemic/nails_seg_yolov8/resolve/187ebf22c110e38d4f9f60ff2b04b29629cff11c/nails_seg_s_yolov8_v1.pt' -o "$nail_build/model.pt"
printf '%s  %s\n' '99b7d1c6ceb4bde32d80fe7ae8c8eb809c27d99b55cf9db54b6692afe68f4070' "$nail_build/model.pt" | sha256sum -c -
nail_docker=(env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host=unix:///var/run/docker.sock)
DOCKER_BUILDKIT=1 "${nail_docker[@]}" build --secret id=system_ca,src=/etc/ssl/certs/ca-certificates.crt -t nail-export:local "$nail_root/scripts/export"
cp "$nail_root/scripts/export/export.py" "$nail_build/output/export.py"
chmod 644 "$nail_build/model.pt" "$nail_build/output/export.py"
chmod 777 "$nail_build/output"
"${nail_docker[@]}" run --rm --network none --user 65534:65534 --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 6g --cpus 4 --tmpfs /tmp:rw,nosuid,nodev,size=2g -e HTTP_PROXY= -e HTTPS_PROXY= -e ALL_PROXY= --mount "type=bind,src=$nail_build/model.pt,dst=/input/model.pt,readonly" --mount "type=bind,src=$nail_build/output,dst=/output" nail-export:local python /output/export.py
python3 "$nail_root/scripts/compress-model.py" "$nail_build/output/nails-fp32.onnx" "$nail_build/compressed"
printf 'Exported ONNX candidates: %s\n' "$nail_build/compressed"
