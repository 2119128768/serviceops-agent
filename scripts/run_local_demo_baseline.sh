#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

unset RUN_LORA

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

cat <<EOF
Starting ServiceOps Agent baseline local demo.

Backend URL: http://${HOST}:${PORT}
Frontend console: http://${HOST}:${PORT}/
API docs: http://${HOST}:${PORT}/docs

This baseline path does not require GPU or a local base model.
EOF

exec python3 -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload

