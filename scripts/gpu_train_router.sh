#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-serviceops-gpu}"
REMOTE_DIR="${REMOTE_DIR:-/root/serviceops-agent}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN="${DRY_RUN:-0}"

RSYNC_EXCLUDES=(
  --exclude ".git/"
  --exclude "outputs/"
  --exclude ".venv/"
  --exclude "__pycache__/"
  --exclude ".pytest_cache/"
  --exclude "*.pyc"
  --exclude "serviceops.db"
)

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

echo "Syncing repo to ${REMOTE_HOST}:${REMOTE_DIR}"
run ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_DIR}'"
run rsync -az --delete "${RSYNC_EXCLUDES[@]}" "${LOCAL_DIR}/" "${REMOTE_HOST}:${REMOTE_DIR}/"

REMOTE_CMD=$(cat <<SH
set -euo pipefail
cd "${REMOTE_DIR}"
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[dev,training]'
nvidia-smi
python3 training/train_sft.py --config training/configs/router_lora_qwen.yaml --dry-run
accelerate launch training/train_sft.py --config training/configs/router_lora_qwen.yaml
python3 training/evaluate_router.py \
  --mode lora \
  --base_model Qwen/Qwen2.5-3B-Instruct \
  --adapter outputs/router-lora-v1 \
  --test_file data/sft_router/test.jsonl \
  --output reports/router_eval_results.jsonl
SH
)

run ssh "${REMOTE_HOST}" "${REMOTE_CMD}"
run mkdir -p "${LOCAL_DIR}/outputs" "${LOCAL_DIR}/reports"
run rsync -az "${REMOTE_HOST}:${REMOTE_DIR}/outputs/router-lora-v1" "${LOCAL_DIR}/outputs/"
run rsync -az "${REMOTE_HOST}:${REMOTE_DIR}/reports/router_sft_report.md" "${LOCAL_DIR}/reports/"

echo "Router training workflow complete."
