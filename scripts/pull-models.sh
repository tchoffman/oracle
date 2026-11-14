#!/usr/bin/env bash
# Pull LLM + embedding model via Ollama. Reads the install config so what gets
# pulled matches what `pergamon ask` will actually use.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v ollama >/dev/null 2>&1; then
  echo "Error: ollama not on PATH. Run 'make deps' first." >&2
  exit 1
fi

# Ensure the server is up.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Starting Ollama server"
  (nohup ollama serve >/dev/null 2>&1 &) || true
  sleep 2
fi

PY=build/venv/bin/python
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

# Resolve which models to pull from the merged install config.
MODELS=()
while IFS= read -r m; do
  [[ -n "$m" ]] && MODELS+=("$m")
done < <("$PY" - <<'PY'
import sys
try:
    from rag.install_config import load_effective_config, load_model_catalog
    eff = load_effective_config()
    cat = load_model_catalog()
    for role in ("primary", "embedding"):
        picked = (eff.get("models") or {}).get(role)
        if picked and picked in cat[role]:
            print(cat[role][picked]["ollama_tag"])
        elif picked:
            print(f"# WARN unknown model id in config: {picked}", file=sys.stderr)
except Exception as e:
    # Fall back to the legacy models.yaml if install config fails.
    print(f"# WARN install config unavailable ({e}); falling back to rag/models.yaml",
          file=sys.stderr)
    import yaml
    with open("rag/models.yaml") as f:
        data = yaml.safe_load(f) or {}
    for key in ("primary", "embedding"):
        for tag in data.get(key) or []:
            print(tag.split("#")[0].strip())
PY
)

if [[ ${#MODELS[@]} -eq 0 ]]; then
  echo "Error: no models resolved from install config." >&2
  exit 1
fi

echo "==> Pulling ${#MODELS[@]} model(s) via Ollama"
for m in "${MODELS[@]}"; do
  echo "  [+] ollama pull $m"
  ollama pull "$m"
done

echo "==> Models ready"
ollama list
