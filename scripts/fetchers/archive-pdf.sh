#!/usr/bin/env bash
# Fetch a single PDF (typically from archive.org or a direct URL).
#
# Env vars:
#   PDF_URL     — source URL
#   OUTPUT_NAME — local filename stem
#
# Example:
#   PDF_URL=https://... OUTPUT_NAME=fm-21-76 scripts/fetchers/archive-pdf.sh

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

: "${PDF_URL:?required}"
: "${OUTPUT_NAME:?required}"

out="$PDF_DIR/${OUTPUT_NAME}.pdf"
fetch_url "$PDF_URL" "$out" 900
