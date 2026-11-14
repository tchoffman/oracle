#!/usr/bin/env bash
# Fetch a single PDF (typically from archive.org or a direct URL).
#
# Env vars:
#   PDF_URL             — primary source URL
#   PDF_URL_FALLBACKS   — optional, comma-separated fallback URLs tried in order
#                         if the primary fails. Useful for flaky CDNs.
#   OUTPUT_NAME         — local filename stem

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

: "${PDF_URL:?required}"
: "${OUTPUT_NAME:?required}"

out="$PDF_DIR/${OUTPUT_NAME}.pdf"

# Try primary first, then each fallback.
urls=("$PDF_URL")
if [[ -n "${PDF_URL_FALLBACKS:-}" ]]; then
  IFS=',' read -r -a fallbacks <<< "$PDF_URL_FALLBACKS"
  for u in "${fallbacks[@]}"; do
    [[ -n "$u" ]] && urls+=("$u")
  done
fi

for i in "${!urls[@]}"; do
  u="${urls[$i]}"
  label="primary"
  [[ "$i" -gt 0 ]] && label="fallback $i"
  log "trying $label: $u"
  if fetch_url "$u" "$out" 600; then
    exit 0
  fi
  warn "$label failed, trying next"
done

err "all URLs failed for $OUTPUT_NAME"
exit 1
