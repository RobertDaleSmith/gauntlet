#!/usr/bin/env bash
# Serve the Gauntlet harness + Tetris game + dashboard at http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || uv venv .venv
uv pip install --python .venv -q -r requirements.txt
exec .venv/bin/python -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port "${PORT:-8000}"
