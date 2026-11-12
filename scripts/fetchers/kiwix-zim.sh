#!/usr/bin/env bash
# Fetch a ZIM from download.kiwix.org, resolving the latest dated file for a prefix.
#
# Env vars (required):
#   KIWIX_PROJECT  — directory under https://download.kiwix.org/zim/
#   KIWIX_PREFIX   — filename prefix (match this + newest date)
#   OUTPUT_NAME    — stable local filename (without .zim extension)
#
# Example:
#   KIWIX_PROJECT=wikipedia KIWIX_PREFIX=wikipedia_en_all_nopic_ \
#     OUTPUT_NAME=wikipedia-en-nopic scripts/fetchers/kiwix-zim.sh

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

: "${KIWIX_PROJECT:?required}"
: "${KIWIX_PREFIX:?required}"
: "${OUTPUT_NAME:?required}"

out="$ZIM_DIR/${OUTPUT_NAME}.zim"

log "resolving latest kiwix://$KIWIX_PROJECT/$KIWIX_PREFIX*.zim"
latest_file="$("$PY" - <<PY
import urllib.request, re, sys
url = "https://download.kiwix.org/zim/${KIWIX_PROJECT}/"
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        html = r.read().decode("utf-8", errors="ignore")
except Exception as e:
    print("", end=""); sys.exit(1)
cands = re.findall(r'(${KIWIX_PREFIX//./\\.}[^"<>\s]+\.zim)', html)
print(sorted(set(cands))[-1] if cands else "", end="")
PY
)"

if [[ -z "$latest_file" ]]; then
  err "no files matched $KIWIX_PREFIX under /zim/$KIWIX_PROJECT/"
  exit 1
fi

full_url="https://download.kiwix.org/zim/$KIWIX_PROJECT/$latest_file"
log "  → $full_url"
fetch_url "$full_url" "$out" 7200
