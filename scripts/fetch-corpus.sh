#!/usr/bin/env bash
# Config-driven corpus dispatcher.
#
# Reads config/install.local.yaml (merged with config/install.yaml and the named
# preset) and runs the appropriate fetcher per enabled item.
#
# Idempotent — individual fetchers skip already-complete downloads.
#
# Usage:
#   scripts/fetch-corpus.sh              # obey install config
#   DRY_RUN=1 scripts/fetch-corpus.sh    # print the plan without downloading

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x build/venv/bin/python ]]; then
  echo "Error: Python venv not built. Run 'make venv' first." >&2
  exit 1
fi
PY=build/venv/bin/python

# Produce a tab-separated plan: fetcher<TAB>env1=val1;env2=val2
PLAN="$(
"$PY" - <<'PY'
import sys
from rag.install_config import load_catalog, load_effective_config, item_size_mb

catalog = load_catalog()
cfg = load_effective_config()
enable = cfg["enable"]

if not enable:
    print("# Nothing enabled in install config.", file=sys.stderr)
    sys.exit(0)

for item_id, opts in enable.items():
    item = catalog.get(item_id)
    if not item:
        print(f"# WARN unknown item: {item_id}", file=sys.stderr)
        continue
    fetcher = item.get("fetcher")
    opts = opts or {}
    merged_opts = {**(item.get("defaults") or {}), **opts}
    env_pairs = []

    if fetcher == "kiwix-zim":
        kcfg = item.get("kiwix", {})
        variant = merged_opts.get("variant") or next(iter(kcfg.get("prefix_by_variant") or {"":""}))
        prefix = (kcfg.get("prefix_by_variant") or {}).get(variant)
        if not prefix:
            print(f"# WARN no kiwix prefix for variant '{variant}' on {item_id}", file=sys.stderr)
            continue
        env_pairs = [
            f"KIWIX_PROJECT={kcfg['project']}",
            f"KIWIX_PREFIX={prefix}",
            f"OUTPUT_NAME={item_id}",
        ]
    elif fetcher == "archive-pdf":
        env_pairs = [
            f"PDF_URL={item['archive']['url']}",
            f"OUTPUT_NAME={item_id}",
        ]
        fallbacks = item["archive"].get("url_fallbacks") or []
        if fallbacks:
            env_pairs.append(f"PDF_URL_FALLBACKS={','.join(fallbacks)}")
    elif fetcher == "gutenberg":
        env_pairs = [f"GUTENBERG_TOP_N={merged_opts.get('top_n', 100)}"]
    elif fetcher == "stackexchange":
        sites = merged_opts.get("sites") or []
        env_pairs = [f"SE_SITES={','.join(sites)}"]
    elif fetcher == "mirror-site":
        m = item.get("mirror", {})
        env_pairs = [
            f"MIRROR_URL={m['seed_url']}",
            f"MIRROR_ALLOWED_HOSTS={','.join(m.get('allowed_hosts') or [])}",
            f"MIRROR_DEPTH={m.get('depth', 3)}",
            f"OUTPUT_NAME={item_id}",
        ]
    elif fetcher == "osmand-region":
        regions = merged_opts.get("regions") or []
        if not regions:
            continue
        env_pairs = [f"OSM_REGIONS={','.join(regions)}"]
    else:
        print(f"# WARN unknown fetcher '{fetcher}' for {item_id}", file=sys.stderr)
        continue

    size = item_size_mb(item, merged_opts)
    size_str = f"{size} MB" if size else "?"
    print(f"{fetcher}\t{item_id}\t{size_str}\t{';'.join(env_pairs)}")
PY
)"

if [[ -z "$PLAN" ]]; then
  echo "Nothing to fetch. Run 'make setup' or edit config/install.local.yaml."
  exit 0
fi

echo "==> Fetch plan"
printf "  %-18s %-28s %s\n" "fetcher" "item" "size"
printf "  %-18s %-28s %s\n" "------"  "----"  "----"
while IFS=$'\t' read -r fetcher item size envs; do
  printf "  %-18s %-28s %s\n" "$fetcher" "$item" "$size"
done <<< "$PLAN"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo ""
  echo "DRY_RUN=1 — not fetching."
  exit 0
fi

echo ""
echo "==> Executing"
while IFS=$'\t' read -r fetcher item size envs; do
  echo ""
  echo "---- $item ($fetcher, $size) ----"
  # Convert "k=v;k=v" to inline env for a single invocation
  env_assignments=()
  IFS=';' read -r -a parts <<< "$envs"
  for p in "${parts[@]}"; do
    env_assignments+=("$p")
  done
  env "${env_assignments[@]}" "scripts/fetchers/${fetcher}.sh" || {
    echo "    !! $item failed; continuing"
  }
done <<< "$PLAN"

echo ""
echo "==> Corpus summary"
"$PY" -m rag.status 2>/dev/null | tail -15 || true
