#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "Starting ServiceOps Agent local demo..."
echo "Backend URL: http://${HOST}:${PORT}"
echo "Frontend console: http://${HOST}:${PORT}/"
echo "API docs: http://${HOST}:${PORT}/docs"
echo
echo "This local demo uses the baseline CPU-safe runtime by default."
echo "LoRA adapters are available under outputs/ but are not required for the local FastAPI demo."
echo

exec python3 -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
