#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p models model_cache/hf model_cache/torch logs reports

export HF_HOME="$PWD/model_cache/hf"
export TRANSFORMERS_CACHE="$PWD/model_cache/hf"
export HF_DATASETS_CACHE="$PWD/model_cache/hf"
export TORCH_HOME="$PWD/model_cache/torch"
export TOKENIZERS_PARALLELISM=false

BASE_MODEL_ID="${BASE_MODEL_ID:-Qwen/Qwen2.5-3B-Instruct}"
LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-models/Qwen2.5-3B-Instruct}"

echo "Local cache:"
echo "  HF_HOME=$HF_HOME"
echo "  TORCH_HOME=$TORCH_HOME"
echo "Local model target:"
echo "  $LOCAL_MODEL_DIR"

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import subprocess
import sys

packages = {
    "torch": "torch",
    "huggingface_hub": "huggingface-hub",
    "transformers": "transformers",
    "peft": "peft",
    "accelerate": "accelerate",
    "sentencepiece": "sentencepiece",
    "google.protobuf": "protobuf",
    "safetensors": "safetensors",
}

missing = [pip_name for module_name, pip_name in packages.items() if importlib.util.find_spec(module_name) is None]
if missing:
    print("Installing missing local inference dependencies:", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
else:
    print("Local inference dependencies are already installed.")
PY

if [[ "${DOWNLOAD_BASE_MODEL:-0}" != "1" ]]; then
  cat <<EOF

Base model download was not requested.

To download the base model locally, run:
  DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh

To use an existing local copy, set:
  LOCAL_BASE_MODEL_PATH=/path/to/Qwen2.5-3B-Instruct

Adapter-only inference is impossible; the Router and Verifier adapters require the base model.
EOF
  exit 0
fi

mkdir -p "$LOCAL_MODEL_DIR"
if command -v hf >/dev/null 2>&1; then
  hf download "$BASE_MODEL_ID" \
    --local-dir "$LOCAL_MODEL_DIR"
elif command -v huggingface-cli >/dev/null 2>&1; then
  huggingface-cli download "$BASE_MODEL_ID" \
    --local-dir "$LOCAL_MODEL_DIR"
else
  python3 - <<PY
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="${BASE_MODEL_ID}",
    local_dir="${LOCAL_MODEL_DIR}",
    local_dir_use_symlinks=False,
)
PY
fi

echo "Downloaded base model to $LOCAL_MODEL_DIR"
