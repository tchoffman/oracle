#!/usr/bin/env bash
# Ingest ZIM articles into the Chroma collection.
#
# Usage:
#   scripts/build-zim-index.sh                     # all ZIMs under build/corpus/zims
#   scripts/build-zim-index.sh path/to/some.zim    # specific ZIM(s)
#   ZIM_LIMIT=500 scripts/build-zim-index.sh       # cap to 500 articles per ZIM
set -euo pipefail

cd "$(dirname "$0")/.."

VENV_PY="build/venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: venv not built. Run 'make venv' first." >&2
  exit 1
fi

# Ensure Ollama is up (embedding endpoint hammered during ingest).
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Starting Ollama server"
  (nohup ollama serve >/dev/null 2>&1 &) || true
  sleep 2
fi

if [[ $# -eq 0 ]]; then
  # Default: all ZIMs under build/corpus/zims.
  # Portable alternative to mapfile (bash 3.2 on macOS).
  zims=()
  while IFS= read -r -d '' f; do
    zims+=("$f")
  done < <(find build/corpus/zims -maxdepth 1 -type f -name "*.zim" -print0 2>/dev/null)
  if [[ ${#zims[@]} -eq 0 ]]; then
    echo "No ZIMs found under build/corpus/zims. Run 'make corpus' first." >&2
    exit 1
  fi
  set -- "${zims[@]}"
fi

exec "$VENV_PY" -m rag.zim_ingest "$@"
