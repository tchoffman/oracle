#!/usr/bin/env bash
# Fetch OsmAnd regional map packs (Geofabrik-sourced).
#
# Env vars:
#   OSM_REGIONS — comma-separated region codes.
#                Examples: "us-northcarolina", "us-georgia", "us-virginia"
#                Full list: https://download.osmand.net/list.php
#
# Puts each region at build/corpus/maps/<region>.obf.zip. OsmAnd on Android/iOS
# can consume these directly; headless use via the obf tool is possible but out
# of scope for v0.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

: "${OSM_REGIONS:?required (comma-separated region codes)}"

IFS=',' read -r -a regions <<< "$OSM_REGIONS"

for region in "${regions[@]}"; do
  region="$(echo "$region" | xargs)"
  [[ -z "$region" ]] && continue
  # OsmAnd map archives are typically named <Region>_<country>_2.obf.zip with
  # title-cased segments; we try both the all-lower and title-cased forms.
  for variant in "$region" "$(echo "$region" | awk '{for(i=1;i<=NF;i++)$i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')"; do
    url="https://download.osmand.net/download?standard=yes&file=${variant}.obf.zip"
    out="$MAP_DIR/${region}.obf.zip"
    if fetch_url "$url" "$out" 1800; then
      break
    fi
    rm -f "$out"
  done
done
