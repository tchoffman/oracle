#!/usr/bin/env bash
# Fetch Stack Exchange data dumps for the named sites.
#
# Env vars:
#   SE_SITES — comma-separated short names (outdoors, cooking, diy, ...)
#
# Each site becomes build/corpus/stackexchange/<site>.stackexchange.com.7z
# (keeping the native archive format — Chroma ingest can extract on demand).
#
# Source: https://archive.org/details/stackexchange — dumps live under
# https://archive.org/download/stackexchange/<site>.stackexchange.com.7z

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

: "${SE_SITES:?required (comma-separated site names)}"

SE_DIR="$CORPUS_DIR/stackexchange"
mkdir -p "$SE_DIR"

IFS=',' read -r -a sites <<< "$SE_SITES"

for site in "${sites[@]}"; do
  site="$(echo "$site" | xargs)"  # trim whitespace
  [[ -z "$site" ]] && continue

  # Meta sites share the same prefix; "stackoverflow" is its own split dump.
  case "$site" in
    stackoverflow)
      url="https://archive.org/download/stackexchange/stackoverflow.com-Posts.7z"
      out="$SE_DIR/stackoverflow.com-Posts.7z"
      warn "stackoverflow dump is 25+ GB; this is a single posts archive"
      ;;
    *)
      url="https://archive.org/download/stackexchange/${site}.stackexchange.com.7z"
      out="$SE_DIR/${site}.stackexchange.com.7z"
      ;;
  esac

  fetch_url "$url" "$out" 1800 || warn "skipping $site after failure"
done
