#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export RUN_LORA=1
export LOCAL_BASE_MODEL_PATH="${LOCAL_BASE_MODEL_PATH:-models/Qwen2.5-3B-Instruct}"
export ROUTER_ADAPTER_PATH="${ROUTER_ADAPTER_PATH:-outputs/router-lora-v1}"
export VERIFIER_ADAPTER_PATH="${VERIFIER_ADAPTER_PATH:-outputs/verifier-lora-v1}"
export LOCAL_LORA_DEVICE="${LOCAL_LORA_DEVICE:-auto}"
export LOCAL_LORA_MAX_NEW_TOKENS="${LOCAL_LORA_MAX_NEW_TOKENS:-128}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! bash scripts/check_local_model.sh; then
  cat <<'EOF'

Local LoRA demo cannot start because the base model is missing or incomplete.

Download it with:
  DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh

Or sync it from a server with:
  REMOTE_HOST=root@your-server REMOTE_MODEL_DIR=/root/models/Qwen2.5-3B-Instruct bash scripts/sync_base_model_from_server.sh
EOF
  exit 2
fi

cat <<EOF
Starting ServiceOps Agent with local Router/Verifier LoRA runtime.

Backend URL: http://${HOST}:${PORT}
Frontend console: http://${HOST}:${PORT}/
API docs: http://${HOST}:${PORT}/docs

Sample ticket:
  我们调用模型 API 一直返回 429，提示 quota exceeded，昨天刚充值。request_id: req_20260427_001

CPU/MPS inference may be slow. Full LoRA E2E eval is better on GPU.
EOF

exec python3 -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
