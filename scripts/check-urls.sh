#!/usr/bin/env bash
# Validate that every URL the catalog could produce is reachable — without
# downloading. Catches stale Kiwix date prefixes, 404s from moved archive.org
# items, mirror seeds that have gone away.
#
# Usage:
#   scripts/check-urls.sh              # check all items in the plan
#   scripts/check-urls.sh --all        # check every item in the catalog
#
# Exits 0 if all URLs OK, non-zero if any failed.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x build/venv/bin/python ]]; then
  echo "Error: Python venv not built. Run 'make venv' first." >&2
  exit 1
fi
PY=build/venv/bin/python

MODE="plan"
if [[ "${1:-}" == "--all" ]]; then
  MODE="all"
fi

"$PY" - "$MODE" <<'PY'
"""Check every URL the catalog could produce.

For kiwix items: resolve the latest dated file for each variant, HEAD the URL.
For archive-pdf items: HEAD the URL directly.
For mirror-site items: HEAD the seed_url.
For gutenberg: HEAD a known top-100 book URL.
For stackexchange: HEAD the archive.org dump for each site.
For osmand-region: skip (regions are free-text and user-specified).
"""
import sys
import urllib.request
import re
import ssl

mode = sys.argv[1] if len(sys.argv) > 1 else "plan"

from rag.install_config import load_catalog, load_effective_config

catalog = load_catalog()

if mode == "all":
    # Expand every option combination for every item.
    plan = []
    for item_id, item in catalog.items():
        fetcher = item["fetcher"]
        defaults = item.get("defaults") or {}
        if fetcher == "kiwix-zim":
            for variant in (item.get("kiwix", {}).get("prefix_by_variant") or {}):
                plan.append((item_id, item, fetcher, {"variant": variant}))
        elif fetcher == "stackexchange":
            # Check every site listed in the options.
            sites = []
            for opt in (item.get("options") or []):
                if opt["name"] == "sites":
                    sites = [c["value"] for c in opt.get("choices", [])]
            for site in sites:
                plan.append((item_id, item, fetcher, {"sites": [site]}))
        else:
            plan.append((item_id, item, fetcher, dict(defaults)))
else:
    # Only check items that would be fetched by the current install config.
    cfg = load_effective_config()
    plan = []
    for item_id, opts in cfg["enable"].items():
        item = catalog.get(item_id)
        if not item:
            print(f"? unknown item in config: {item_id}")
            continue
        plan.append((item_id, item, item["fetcher"], opts or {}))


def head(url: str) -> tuple[bool, str]:
    """Return (ok, info)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            size = r.headers.get("Content-Length") or "?"
            return True, f"HTTP {r.status} ({size} bytes)"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def resolve_kiwix_latest(project: str, prefix: str) -> str | None:
    url = f"https://download.kiwix.org/zim/{project}/"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None
    cands = re.findall(rf'({re.escape(prefix)}[^"<>\s]+\.zim)', html)
    if not cands:
        return None
    return f"{url}{sorted(set(cands))[-1]}"


def check(item_id: str, item: dict, fetcher: str, opts: dict):
    """Check one item under the given opts. Return list of (label, ok, info)."""
    rows = []
    if fetcher == "kiwix-zim":
        kcfg = item.get("kiwix", {})
        variant = opts.get("variant") or next(iter(kcfg.get("prefix_by_variant") or {"":""}))
        prefix = (kcfg.get("prefix_by_variant") or {}).get(variant)
        if not prefix:
            rows.append((f"{item_id}[{variant}]", False, "no prefix for this variant"))
            return rows
        resolved = resolve_kiwix_latest(kcfg["project"], prefix)
        if resolved is None:
            rows.append((f"{item_id}[{variant}]", False, f"no files match {prefix} under /zim/{kcfg['project']}/"))
        else:
            ok, info = head(resolved)
            short = resolved.split("/")[-1]
            rows.append((f"{item_id}[{variant}] → {short}", ok, info))

    elif fetcher == "archive-pdf":
        url = item["archive"]["url"]
        ok, info = head(url)
        rows.append((item_id, ok, info))

    elif fetcher == "mirror-site":
        url = item["mirror"]["seed_url"]
        ok, info = head(url)
        rows.append((f"{item_id} (seed)", ok, info))

    elif fetcher == "gutenberg":
        # Validate that Gutenberg's top-100 page is reachable.
        url = "https://www.gutenberg.org/browse/scores/top"
        ok, info = head(url)
        rows.append((f"{item_id} (top-100 index)", ok, info))

    elif fetcher == "stackexchange":
        sites = opts.get("sites") or []
        if not sites:
            # Use the default from catalog.
            defs = item.get("defaults") or {}
            sites = defs.get("sites") or ["outdoors"]
        for site in sites:
            url = f"https://archive.org/download/stackexchange/{site}.stackexchange.com.7z"
            ok, info = head(url)
            rows.append((f"{item_id}[{site}]", ok, info))

    elif fetcher == "osmand-region":
        rows.append((item_id, True, "skipped (regions are user-specified free text)"))

    else:
        rows.append((item_id, False, f"unknown fetcher: {fetcher}"))

    return rows


all_rows = []
for item_id, item, fetcher, opts in plan:
    for row in check(item_id, item, fetcher, opts):
        all_rows.append(row)

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

n_ok = n_fail = 0
for label, ok, info in all_rows:
    tag = f"{GREEN} ok {RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{tag}] {label:<55} {info}")
    if ok:
        n_ok += 1
    else:
        n_fail += 1

print(f"\n{n_ok} OK, {n_fail} FAIL")
sys.exit(1 if n_fail else 0)
PY
