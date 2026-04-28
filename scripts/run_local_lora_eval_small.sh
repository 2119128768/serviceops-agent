#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p reports
REPORT="reports/local_lora_e2e_small.md"
LIMIT="${LIMIT:-5}"
export LOCAL_LORA_MAX_NEW_TOKENS="${LOCAL_LORA_MAX_NEW_TOKENS:-96}"
DATASET="${DATASET:-data/eval/manual_holdout_e2e.jsonl}"
OUTPUT="${OUTPUT:-reports/local_lora_e2e_small_results.jsonl}"

if ! bash scripts/check_local_model.sh >/tmp/serviceops_local_model_check.out 2>&1; then
  {
    echo "# Local LoRA E2E Small Eval"
    echo
    echo "Small local LoRA E2E eval was not run because the base model is missing or incomplete."
    echo
    echo '```'
    cat /tmp/serviceops_local_model_check.out
    echo '```'
    echo
    echo "Download the base model with:"
    echo
    echo "    DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh"
  } > "$REPORT"
  cat "$REPORT"
  exit 2
fi

python3 -m backend.evals.run_eval \
  --dataset "$DATASET" \
  --mode agent_router_lora_verifier_lora \
  --use-local-lora \
  --base-model-path "${LOCAL_BASE_MODEL_PATH:-models/Qwen2.5-3B-Instruct}" \
  --router-adapter "${ROUTER_ADAPTER_PATH:-outputs/router-lora-v1}" \
  --verifier-adapter "${VERIFIER_ADAPTER_PATH:-outputs/verifier-lora-v1}" \
  --limit "$LIMIT" \
  --output "$OUTPUT" | tee /tmp/serviceops_local_lora_eval_small.out

{
  echo "# Local LoRA E2E Small Eval"
  echo
  echo "- dataset: \`$DATASET\`"
  echo "- limit: \`$LIMIT\`"
  echo "- output: \`$OUTPUT\`"
  echo
  echo '```json'
  cat /tmp/serviceops_local_lora_eval_small.out
  echo '```'
} > "$REPORT"

cat "$REPORT"
