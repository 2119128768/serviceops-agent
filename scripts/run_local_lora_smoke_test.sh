#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p reports
REPORT="reports/local_lora_smoke_test.md"
export LOCAL_LORA_MAX_NEW_TOKENS="${LOCAL_LORA_MAX_NEW_TOKENS:-96}"

if ! bash scripts/check_local_model.sh >/tmp/serviceops_local_model_check.out 2>&1; then
  {
    echo "# Local LoRA Smoke Test"
    echo
    echo "Local LoRA smoke test was not run because the base model is missing or incomplete."
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

python3 - <<'PY' | tee "$REPORT"
from __future__ import annotations

import json
import os

from backend.llm.local_lora_runtime import LocalLoRAJsonModel

runtime = LocalLoRAJsonModel(
    base_model_path_or_id=os.getenv("LOCAL_BASE_MODEL_PATH", "models/Qwen2.5-3B-Instruct"),
    router_adapter_path=os.getenv("ROUTER_ADAPTER_PATH", "outputs/router-lora-v1"),
    verifier_adapter_path=os.getenv("VERIFIER_ADAPTER_PATH", "outputs/verifier-lora-v1"),
    device=os.getenv("LOCAL_LORA_DEVICE", "auto"),
    max_new_tokens=int(os.getenv("LOCAL_LORA_MAX_NEW_TOKENS", "256")),
)
result = runtime.smoke_test()

print("# Local LoRA Smoke Test")
print()
print("```json")
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
print("```")
PY
