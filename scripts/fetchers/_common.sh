#!/usr/bin/env bash
# Shared helpers for fetcher scripts. Source this at the top of each fetcher.
# Not intended to be executed directly.

set -euo pipefail

# Resolve paths relative to repo root.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
CORPUS_DIR="$BUILD_DIR/corpus"
ZIM_DIR="$CORPUS_DIR/zims"
PDF_DIR="$CORPUS_DIR/pdfs"
BOOK_DIR="$CORPUS_DIR/books"
MIRROR_DIR="$CORPUS_DIR/mirrors"
MAP_DIR="$CORPUS_DIR/maps"

mkdir -p "$ZIM_DIR" "$PDF_DIR" "$BOOK_DIR" "$MIRROR_DIR" "$MAP_DIR"

log()  { printf "  %s\n" "$*"; }
ok()   { printf "  [\033[32m ok \033[0m] %s\n" "$*"; }
err()  { printf "  [\033[31merr \033[0m] %s\n" "$*" >&2; }
warn() { printf "  [\033[33mwarn\033[0m] %s\n" "$*"; }

# Idempotent curl. Resumes partial files. --max-time caps total transfer.
# Usage: fetch_url <url> <output-path> [max-time-seconds]
fetch_url() {
  local url="$1" out="$2" max="${3:-1800}"
  if [[ -s "$out" ]]; then
    # If we already have the file at expected size, don't refetch.
    local have have_remote
    have="$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out" 2>/dev/null || echo 0)"
    have_remote="$(curl -sIL --max-time 15 "$url" | awk '/^[Cc]ontent-[Ll]ength:/ {print $2}' | tr -d '\r' | tail -1)"
    if [[ -n "$have_remote" && "$have" == "$have_remote" ]]; then
      ok "already have $(basename "$out") ($(du -h "$out" | cut -f1))"
      return 0
    fi
  fi
  log "fetching $(basename "$out")"
  if curl -L --fail --retry 5 --retry-delay 10 --retry-all-errors \
          --max-time "$max" --continue-at - -o "$out" "$url"; then
    ok "done $(basename "$out")"
  else
    err "download failed; partial file kept — re-run to resume"
    return 1
  fi
}

# Python used by fetcher scripts (venv preferred for YAML parsing + 3.11 syntax).
if [[ -x "$REPO_ROOT/build/venv/bin/python" ]]; then
  PY="$REPO_ROOT/build/venv/bin/python"
else
  PY="python3"
fi
export PY
