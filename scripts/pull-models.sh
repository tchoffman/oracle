#!/usr/bin/env bash
# Pull LLM + embedding model via Ollama. Idempotent.
# Edit MODELS_YAML to change which models get pulled.
set -euo pipefail

cd "$(dirname "$0")/.."

MODELS_YAML="rag/models.yaml"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Error: ollama not on PATH. Run 'make deps' first." >&2
  exit 1
fi

# Ensure the server is up
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Starting Ollama server"
  (nohup ollama serve >/dev/null 2>&1 &) || true
  sleep 2
fi

# Extract model tags from models.yaml. Portable (bash 3.2 on macOS lacks mapfile).
MODELS=()
while IFS= read -r m; do
  [[ -n "$m" ]] && MODELS+=("$m")
done < <(awk '
  /^[a-zA-Z_]+:$/ { inlist=1; next }
  inlist && /^[[:space:]]*-[[:space:]]+/ {
    gsub(/^[[:space:]]*-[[:space:]]+/, "")
    gsub(/[[:space:]]*#.*$/, "")
    if ($0 != "") print
  }
' "$MODELS_YAML")

if [[ ${#MODELS[@]} -eq 0 ]]; then
  echo "Error: no models found in $MODELS_YAML" >&2
  exit 1
fi

echo "==> Pulling ${#MODELS[@]} model(s) via Ollama"
for m in "${MODELS[@]}"; do
  echo "  [+] ollama pull $m"
  ollama pull "$m"
done

echo "==> Models ready"
ollama list
