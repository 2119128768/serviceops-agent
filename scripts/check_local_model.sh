#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p reports

BASE_MODEL_PATH="${LOCAL_BASE_MODEL_PATH:-models/Qwen2.5-3B-Instruct}"
ROUTER_ADAPTER_PATH="${ROUTER_ADAPTER_PATH:-outputs/router-lora-v1}"
VERIFIER_ADAPTER_PATH="${VERIFIER_ADAPTER_PATH:-outputs/verifier-lora-v1}"
REPORT="reports/local_model_check.md"

tokenizer_found=false
for file in tokenizer.json tokenizer.model vocab.json merges.txt; do
  if [[ -f "$BASE_MODEL_PATH/$file" ]]; then
    tokenizer_found=true
  fi
done

base_found=false
config_found=false
base_weights_found=false
base_weights_status=missing
router_adapter_found=false
verifier_adapter_found=false
inference_possible=false

[[ -d "$BASE_MODEL_PATH" ]] && base_found=true
[[ -f "$BASE_MODEL_PATH/config.json" ]] && config_found=true
if [[ -f "$BASE_MODEL_PATH/model.safetensors.index.json" ]]; then
  if python3 - "$BASE_MODEL_PATH" <<'PY'
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
index_path = base / "model.safetensors.index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
expected = sorted(set(index.get("weight_map", {}).values()))
missing = [name for name in expected if not (base / name).is_file()]
if not expected or missing:
    raise SystemExit(1)
PY
  then
    base_weights_found=true
    base_weights_status=found
  else
    base_weights_status=incomplete
  fi
elif find "$BASE_MODEL_PATH" -maxdepth 1 -type f \( -name "*.safetensors" -o -name "*.bin" -o -name "*.pt" -o -name "*.pth" \) | grep -q .; then
  base_weights_found=true
  base_weights_status=found
fi
[[ -f "$ROUTER_ADAPTER_PATH/adapter_config.json" && ( -f "$ROUTER_ADAPTER_PATH/adapter_model.safetensors" || -f "$ROUTER_ADAPTER_PATH/adapter_model.bin" ) ]] && router_adapter_found=true
[[ -f "$VERIFIER_ADAPTER_PATH/adapter_config.json" && ( -f "$VERIFIER_ADAPTER_PATH/adapter_model.safetensors" || -f "$VERIFIER_ADAPTER_PATH/adapter_model.bin" ) ]] && verifier_adapter_found=true

if [[ "$base_found" == true && "$config_found" == true && "$base_weights_found" == true && "$tokenizer_found" == true && "$router_adapter_found" == true && "$verifier_adapter_found" == true ]]; then
  inference_possible=true
fi

{
  echo "# 本地模型检查"
  echo
  echo "该报告用于判断本地是否已经具备 Router/Verifier LoRA 推理条件。Adapter 不能单独运行，必须和兼容的 base model 一起加载。"
  echo
  echo "| 检查项 | 路径 | 状态 |"
  echo "| --- | --- | --- |"
  echo "| base_model_dir | \`$BASE_MODEL_PATH\` | $([[ "$base_found" == true ]] && echo found || echo base_model_missing) |"
  echo "| config.json | \`$BASE_MODEL_PATH/config.json\` | $([[ "$config_found" == true ]] && echo found || echo missing) |"
  echo "| base model weights | \`$BASE_MODEL_PATH\` | $base_weights_status |"
  echo "| tokenizer files | \`$BASE_MODEL_PATH\` | $([[ "$tokenizer_found" == true ]] && echo found || echo missing) |"
  echo "| router_adapter | \`$ROUTER_ADAPTER_PATH\` | $([[ "$router_adapter_found" == true ]] && echo found || echo missing) |"
  echo "| verifier_adapter | \`$VERIFIER_ADAPTER_PATH\` | $([[ "$verifier_adapter_found" == true ]] && echo found || echo missing) |"
  echo
  echo "## 结论"
  echo
  echo "- local_lora_inference_possible: $inference_possible"
  if [[ "$inference_possible" != true ]]; then
    echo "- status: base_model_missing_or_incomplete"
    echo "- 说明：当前缺少完整的 \`Qwen2.5-3B-Instruct\` base model，因此本地 LoRA smoke test 和 LoRA demo 不能真实运行。"
    echo "- next_step: \`DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh\`"
  else
    echo "- status: ready"
    echo "- 说明：本地 base model、Router adapter、Verifier adapter 均已就绪，可以运行本地 LoRA smoke test。"
  fi
  echo
  echo "注意：Adapter-only inference is impossible；Router/Verifier adapters 必须依赖 base model。"
} > "$REPORT"

cat "$REPORT"

if [[ "$inference_possible" != true ]]; then
  exit 2
fi
