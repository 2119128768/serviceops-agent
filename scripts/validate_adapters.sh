#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT="reports/adapter_validation.md"
mkdir -p reports

adapter_missing=false

check_adapter() {
  local name="$1"
  local dir="$2"
  local has_error=false
  local weight_file=""

  {
    echo "## ${name}"
    echo
  } >> "$REPORT"

  if [[ ! -d "$dir" ]]; then
    echo "- directory: missing \`$dir\`" >> "$REPORT"
    has_error=true
  else
    echo "- directory: found \`$dir\`" >> "$REPORT"
    echo "- size: \`$(du -sh "$dir" | awk '{print $1}')\`" >> "$REPORT"
  fi

  if [[ ! -f "$dir/adapter_config.json" ]]; then
    echo "- adapter_config.json: missing" >> "$REPORT"
    has_error=true
  else
    echo "- adapter_config.json: found" >> "$REPORT"
  fi

  for candidate in "$dir/adapter_model.safetensors" "$dir/adapter_model.bin"; do
    if [[ -f "$candidate" ]]; then
      weight_file="$candidate"
      break
    fi
  done

  if [[ -z "$weight_file" ]]; then
    echo "- adapter weights: missing" >> "$REPORT"
    has_error=true
  else
    echo "- adapter weights: found \`$(basename "$weight_file")\`" >> "$REPORT"
  fi

  if [[ "$has_error" == true ]]; then
    adapter_missing=true
    echo "- status: invalid" >> "$REPORT"
  else
    echo "- status: valid" >> "$REPORT"
  fi
  echo >> "$REPORT"
}

cat > "$REPORT" <<'EOF'
# Adapter Validation

This report validates local PEFT/LoRA adapter directories without printing raw weights.

EOF

check_adapter "Router LoRA" "outputs/router-lora-v1"
check_adapter "Verifier LoRA" "outputs/verifier-lora-v1"

{
  echo "## Summary"
  echo
  echo "- adapter_missing: ${adapter_missing}"
  echo "- generated_by: \`scripts/validate_adapters.sh\`"
} >> "$REPORT"

cat "$REPORT"

if [[ "$adapter_missing" == true ]]; then
  exit 2
fi
