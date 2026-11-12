#!/usr/bin/env bash
# End-to-end smoke test. Validates deps → models → corpus → index → ask.
# Exits non-zero on first failure, printing what broke.
set -euo pipefail

cd "$(dirname "$0")/.."

PY="build/venv/bin/python"

pass() { printf "  [\033[32m ok \033[0m] %s\n" "$1"; }
fail() { printf "  [\033[31mFAIL\033[0m] %s\n" "$1"; exit 1; }
hdr()  { printf "\n== %s ==\n" "$1"; }

hdr "1. Dependencies"
command -v ollama >/dev/null || fail "ollama not on PATH"
pass "ollama binary"

if [[ -x build/bin/kiwix-serve ]] || command -v kiwix-serve >/dev/null || [[ -d /Applications/Kiwix.app ]]; then
  pass "kiwix-serve (headless or GUI)"
else
  fail "no kiwix-serve binary AND no Kiwix.app"
fi

[[ -x "$PY" ]] || fail "Python venv not built — run 'make venv'"
pass "python venv"

hdr "2. Ollama models"
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  (nohup ollama serve >/dev/null 2>&1 &)
  sleep 2
fi
models="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' || true)"
echo "$models" | grep -qi "llama3" || fail "LLM model not pulled — run 'make models'"
pass "LLM model present"
echo "$models" | grep -qi "nomic-embed" || fail "embedding model not pulled"
pass "embedding model present"

hdr "3. Corpus"
pdf_count="$(find build/corpus/pdfs -name '*.pdf' 2>/dev/null | wc -l | tr -d ' ')"
zim_count="$(find build/corpus/zims -name '*.zim' 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$pdf_count" -eq 0 && "$zim_count" -eq 0 ]]; then
  fail "no corpus files at all — run 'make corpus'"
fi
pass "$pdf_count PDF(s), $zim_count ZIM(s) in corpus"

hdr "4. RAG index"
chunk_count="$("$PY" - <<'PY'
import chromadb, sys
from rag.config import load_config
cfg = load_config()
c = chromadb.PersistentClient(path=cfg["chroma_dir"])
try:
    coll = c.get_collection(cfg["chroma_collection"])
    print(coll.count())
except Exception:
    print(0)
PY
)"
if [[ "$chunk_count" -gt 0 ]]; then
  pass "Chroma index has $chunk_count chunks"
else
  if [[ "$pdf_count" -gt 0 ]]; then
    fail "Chroma empty but PDFs present — run 'make index'"
  else
    printf "  [\033[33m--\033[0m] no PDFs to index; skipping\n"
  fi
fi

hdr "5. Ask the pergamon"
answer="$(bin/pergamon ask "In one sentence: why is clean water the top priority after shelter?" 2>&1 | tail -20)"
if echo "$answer" | grep -qi -E "water|dehydrat|hydrat|drink"; then
  pass "pergamon ask produced a plausible answer"
else
  echo "---last 20 lines of pergamon ask output---"
  echo "$answer"
  fail "pergamon ask output didn't contain water-related terms"
fi

echo ""
echo "All smoke tests passed."
