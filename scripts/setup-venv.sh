#!/usr/bin/env bash
# Build a Python venv for the RAG stack. Uses uv if available, falls back to pip.
set -euo pipefail

cd "$(dirname "$0")/.."

VENV="build/venv"
REQS="rag/requirements.txt"

mkdir -p build

if [[ ! -d "$VENV" ]]; then
  echo "==> Creating venv at $VENV"
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV" --python 3.11 || uv venv "$VENV"
  else
    python3 -m venv "$VENV"
  fi
fi

echo "==> Installing requirements from $REQS"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$VENV/bin/python" -r "$REQS"
else
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$REQS"
fi

echo "==> Venv ready"
