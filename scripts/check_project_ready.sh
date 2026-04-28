#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT="${PROJECT_READY_REPORT:-logs/project_ready_check.md}"
mkdir -p "$(dirname "$REPORT")"

failures=0

check_file() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "- $path: found" >> "$REPORT"
  else
    echo "- $path: missing" >> "$REPORT"
    failures=$((failures + 1))
  fi
}

cat > "$REPORT" <<'EOF'
# Project Readiness Check

该报告检查公开展示前的基本条件：关键文档是否存在、模型/缓存/日志是否被 `.gitignore` 忽略、是否误追踪大模型权重或 secrets，以及测试是否通过。

## 必要文件

EOF

check_file "README.md"
check_file "AGENTS.md"
check_file "reports/router_sft_report.md"
check_file "reports/verifier_sft_report.md"
check_file "reports/end_to_end_eval.md"
check_file "reports/manual_holdout_report.md"
check_file "reports/rag_ablation.md"
check_file "reports/failure_analysis.md"
check_file "reports/final_project_summary.md"
check_file "reports/architecture_cn.md"
check_file "reports/local_runtime.md"
check_file "outputs/router-lora-v1/adapter_config.json"
check_file "outputs/verifier-lora-v1/adapter_config.json"

{
  echo
  echo "## 忽略规则检查"
  echo
} >> "$REPORT"

for path in outputs models model_cache hf_cache logs checkpoints wandb .env data/downloads; do
  if git check-ignore -q "$path" 2>/dev/null || git check-ignore -q "$path/" 2>/dev/null; then
    echo "- $path: ignored" >> "$REPORT"
  else
    echo "- $path: not ignored or absent from ignore rules" >> "$REPORT"
    failures=$((failures + 1))
  fi
done

tracked_sensitive="$(git ls-files | grep -E '(^outputs/|^models/|^model_cache/|^hf_cache/|^logs/|\\.safetensors$|\\.bin$|\\.pt$|\\.pth$|^\\.env$)' || true)"
{
  echo
  echo "## 已被 Git 追踪的敏感或大文件"
  echo
} >> "$REPORT"
if [[ -n "$tracked_sensitive" ]]; then
  echo '```' >> "$REPORT"
  echo "$tracked_sensitive" >> "$REPORT"
  echo '```' >> "$REPORT"
  failures=$((failures + 1))
else
  echo "- none" >> "$REPORT"
fi

{
  echo
  echo "## 测试"
  echo
} >> "$REPORT"
if python3 -m pytest -q >> "$REPORT" 2>&1; then
  echo "- pytest: passed" >> "$REPORT"
else
  echo "- pytest: failed" >> "$REPORT"
  failures=$((failures + 1))
fi

{
  echo
  echo "## Git 状态"
  echo
  echo '```'
  git status --short
  echo '```'
  echo
  echo "## 结论"
  echo
  echo "- failures: $failures"
} >> "$REPORT"

cat "$REPORT"

if [[ "$failures" -ne 0 ]]; then
  exit 1
fi
