#!/usr/bin/env bash
set -euo pipefail

vllm serve Qwen/Qwen2.5-3B-Instruct \
  --host 0.0.0.0 \
  --port 8001 \
  --enable-lora \
  --lora-modules router=outputs/router-lora-v1 verifier=outputs/verifier-lora-v1 \
  --max-loras 2 \
  --max-lora-rank 32
