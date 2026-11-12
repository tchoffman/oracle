#!/usr/bin/env bash
# Run the Python ingest over corpus PDFs.
set -euo pipefail

cd "$(dirname "$0")/.."

VENV_PY="build/venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: venv not built. Run 'make venv' first." >&2
  exit 1
fi

# Ensure ollama server is up — ingest will hammer the embed endpoint.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Starting Ollama server"
  (nohup ollama serve >/dev/null 2>&1 &) || true
  sleep 2
fi

"$VENV_PY" -m rag.ingest
