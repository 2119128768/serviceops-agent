#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-models/Qwen2.5-3B-Instruct}"

if [[ -z "${REMOTE_HOST:-}" || -z "${REMOTE_MODEL_DIR:-}" ]]; then
  cat <<'EOF'
Usage:
  REMOTE_HOST=root@your-server REMOTE_MODEL_DIR=/root/models/Qwen2.5-3B-Instruct bash scripts/sync_base_model_from_server.sh

Optional:
  LOCAL_MODEL_DIR=models/Qwen2.5-3B-Instruct

This script intentionally contains no password, token, or private key.
EOF
  exit 1
fi

mkdir -p "$LOCAL_MODEL_DIR"
rsync -avz "${REMOTE_HOST}:${REMOTE_MODEL_DIR}/" "${LOCAL_MODEL_DIR}/"
echo "Synced base model to $LOCAL_MODEL_DIR"

