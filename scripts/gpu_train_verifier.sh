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
python3 training/train_sft.py --config training/configs/verifier_lora_qwen.yaml --dry-run
accelerate launch training/train_sft.py --config training/configs/verifier_lora_qwen.yaml
python3 training/evaluate_verifier.py \
  --mode lora \
  --base_model Qwen/Qwen2.5-3B-Instruct \
  --adapter outputs/verifier-lora-v1 \
  --test_file data/sft_verifier/test.jsonl \
  --output reports/verifier_eval_results.jsonl
SH
)

run ssh "${REMOTE_HOST}" "${REMOTE_CMD}"
run mkdir -p "${LOCAL_DIR}/outputs" "${LOCAL_DIR}/reports"
run rsync -az "${REMOTE_HOST}:${REMOTE_DIR}/outputs/verifier-lora-v1" "${LOCAL_DIR}/outputs/"
run rsync -az "${REMOTE_HOST}:${REMOTE_DIR}/reports/verifier_sft_report.md" "${LOCAL_DIR}/reports/"

echo "Verifier training workflow complete."
