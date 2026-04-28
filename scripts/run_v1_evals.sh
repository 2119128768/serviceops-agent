#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p reports

E2E_LIMIT="${E2E_LIMIT:-30}"
BASE_MODEL="${BASE_MODEL:-${LOCAL_BASE_MODEL_PATH:-Qwen/Qwen2.5-3B-Instruct}}"
RUN_LORA="${RUN_LORA:-0}"

echo "[1/8] pytest"
python3 -m pytest -q

echo "[2/8] adapter validation"
bash scripts/validate_adapters.sh

echo "[3/8] manual holdout files"
python3 data_pipeline/build_manual_holdout.py

echo "[4/8] Router module eval"
python3 training/evaluate_router.py \
  --mode rule \
  --test_file data/sft_router/test.jsonl \
  --output reports/router_eval_rule.jsonl

python3 training/evaluate_router.py \
  --mode prompt \
  --test_file data/sft_router/test.jsonl \
  --output reports/router_eval_prompt.jsonl

if [[ "$RUN_LORA" == "1" ]]; then
  python3 training/evaluate_router.py \
    --mode lora \
    --base_model "$BASE_MODEL" \
    --adapter outputs/router-lora-v1 \
    --test_file data/sft_router/test.jsonl \
    --output reports/router_eval_lora.jsonl
else
  echo "Router LoRA module eval skipped locally. Set RUN_LORA=1 LOCAL_BASE_MODEL_PATH=/path/to/Qwen2.5-3B-Instruct to run it."
fi

echo "[5/8] Verifier module eval"
python3 training/evaluate_verifier.py \
  --mode prompt \
  --test_file data/sft_verifier/test.jsonl \
  --output reports/verifier_eval_prompt.jsonl

if [[ "$RUN_LORA" == "1" ]]; then
  python3 training/evaluate_verifier.py \
    --mode lora \
    --base_model "$BASE_MODEL" \
    --adapter outputs/verifier-lora-v1 \
    --test_file data/sft_verifier/test.jsonl \
    --output reports/verifier_eval_lora.jsonl
else
  echo "Verifier LoRA module eval skipped locally. Set RUN_LORA=1 LOCAL_BASE_MODEL_PATH=/path/to/Qwen2.5-3B-Instruct to run it."
fi

echo "[6/8] Manual holdout baselines"
python3 training/evaluate_router.py \
  --mode rule \
  --test_file data/eval/manual_holdout_router.jsonl \
  --output reports/manual_router_eval_rule.jsonl \
  --report reports/manual_holdout_router_report.md \
  --summary-output reports/manual_router_eval_summary.jsonl

python3 training/evaluate_verifier.py \
  --mode prompt \
  --test_file data/eval/manual_holdout_verifier.jsonl \
  --output reports/manual_verifier_eval_prompt.jsonl \
  --report reports/manual_holdout_verifier_report.md \
  --summary-output reports/manual_verifier_eval_summary.jsonl

echo "[7/8] RAG eval"
python3 -m backend.evals.rag_eval \
  --queries data/eval/rag_eval_hard.jsonl \
  --embedding-backend hash \
  --reranker none \
  --output reports/rag_eval_hash.jsonl

echo "[8/8] E2E eval"
E2E_MODEL_ARGS=(--base-model "$BASE_MODEL")
if [[ "$RUN_LORA" == "1" ]]; then
  E2E_MODEL_ARGS=(--use-local-lora --base-model-path "$BASE_MODEL")
fi
SERVICEOPS_LOCAL_FILES_ONLY=1 python3 -m backend.evals.run_eval \
  --dataset data/eval/end_to_end_eval_hard.jsonl \
  --mode all \
  --limit "$E2E_LIMIT" \
  "${E2E_MODEL_ARGS[@]}" \
  --output reports/end_to_end_eval_results.jsonl
cp reports/end_to_end_eval_details.jsonl reports/hard_end_to_end_eval_details.jsonl
cp reports/failure_analysis_details.jsonl reports/hard_failure_analysis_details.jsonl

SERVICEOPS_LOCAL_FILES_ONLY=1 python3 -m backend.evals.run_eval \
  --dataset data/eval/manual_holdout_e2e.jsonl \
  --mode all \
  --limit "$E2E_LIMIT" \
  "${E2E_MODEL_ARGS[@]}" \
  --output reports/manual_e2e_eval_results.jsonl
cp reports/end_to_end_eval_details.jsonl reports/manual_end_to_end_eval_details.jsonl
cp reports/failure_analysis_details.jsonl reports/manual_failure_analysis_details.jsonl

cat > reports/v1_eval_run_summary.md <<EOF
# v1 Eval Run Summary

- pytest: completed
- adapter validation: completed
- Router rule/prompt module eval: completed
- Router LoRA module eval: $([[ "$RUN_LORA" == "1" ]] && echo "completed" || echo "skipped locally; existing GPU report retained")
- Verifier prompt module eval: completed
- Verifier LoRA module eval: $([[ "$RUN_LORA" == "1" ]] && echo "completed" || echo "skipped locally; existing GPU report retained")
- RAG hash eval: completed
- Hard E2E eval: completed with limit \`$E2E_LIMIT\`
- Manual E2E eval: completed with limit \`$E2E_LIMIT\`

LoRA E2E modes require a local or GPU-accessible Qwen2.5-3B-Instruct base model plus training dependencies.
When unavailable, reports mark those modes as unavailable instead of using proxy metrics.
EOF

python3 data_pipeline/write_v1_reports.py

echo "v1 evals complete. Summary: reports/v1_eval_run_summary.md"
