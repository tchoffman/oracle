#!/usr/bin/env bash
# Download the starter corpus listed in corpus/sources.yaml.
# Idempotent — skips files that already exist with non-zero size.
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCES="corpus/sources.yaml"
ZIM_DIR="build/corpus/zims"
PDF_DIR="build/corpus/pdfs"

mkdir -p "$ZIM_DIR" "$PDF_DIR"

# Parse sources.yaml using Python (already required by the RAG stack).
# Emit tab-separated: type\tname\turl\tmanual\toptional
#   For ZIM entries with kiwix_project/kiwix_prefix, resolve the latest dated file.
python3 - <<'PY' > /tmp/oracle-sources.tsv
import urllib.request, re, yaml, sys

def resolve_kiwix_latest(project: str, prefix: str) -> str | None:
    url = f"https://download.kiwix.org/zim/{project}/"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  WARN: cannot list {url}: {e}", file=sys.stderr)
        return None
    # Find candidate filenames matching prefix and ending in .zim
    candidates = re.findall(rf'({re.escape(prefix)}[^"<>\s]+\.zim)', html)
    if not candidates:
        print(f"  WARN: no files match prefix '{prefix}' under {url}", file=sys.stderr)
        return None
    # The zim files include YYYY-MM dates; sort lexicographically picks the latest.
    latest = sorted(set(candidates))[-1]
    return f"{url}{latest}"

with open("corpus/sources.yaml") as f:
    data = yaml.safe_load(f) or {}

for e in (data.get("zims") or []):
    if e.get("optional"):
        continue
    url = e.get("url")
    if not url and e.get("kiwix_project") and e.get("kiwix_prefix"):
        url = resolve_kiwix_latest(e["kiwix_project"], e["kiwix_prefix"])
    if not url:
        print(f"  SKIP zim {e['name']}: no url resolvable", file=sys.stderr)
        continue
    manual = "1" if e.get("manual") else "0"
    print(f"zims\t{e['name']}\t{url}\t{manual}")

for e in (data.get("pdfs") or []):
    url = e.get("url", "")
    manual = "1" if e.get("manual") else "0"
    print(f"pdfs\t{e['name']}\t{url}\t{manual}")
PY

while IFS=$'\t' read -r kind name url manual; do
  case "$kind" in
    zims) dir="$ZIM_DIR"; ext="zim" ;;
    pdfs) dir="$PDF_DIR"; ext="pdf" ;;
    *) continue ;;
  esac
  out="$dir/$name.$ext"

  if [[ "$manual" == "1" ]]; then
    if [[ -s "$out" ]]; then
      echo "  [ok] $name (manually placed at $out)"
    else
      echo "  [!] $name — manual download required; drop PDF at: $out"
      echo "      Source: $url"
    fi
    continue
  fi

  if [[ -s "$out" ]]; then
    echo "  [ok] $name already downloaded ($(du -h "$out" | cut -f1))"
    continue
  fi

  echo "  [+] fetching $name"
  echo "      $url"
  # -L follow redirects, --retry handles transient network failures,
  # --continue-at - resumes partial downloads from previous runs.
  if ! curl -L --fail --retry 5 --retry-delay 10 --retry-all-errors \
        --continue-at - -o "$out" "$url"; then
    echo "    ...failed; partial file kept so you can resume with another run"
    exit 1
  fi
done < /tmp/oracle-sources.tsv

rm -f /tmp/oracle-sources.tsv

echo ""
echo "==> Corpus summary"
echo "ZIMs:"
ls -lh "$ZIM_DIR" 2>/dev/null | tail -n +2 | awk '{printf "  %s  %s\n", $5, $9}'
echo "PDFs:"
ls -lh "$PDF_DIR" 2>/dev/null | tail -n +2 | awk '{printf "  %s  %s\n", $5, $9}'
