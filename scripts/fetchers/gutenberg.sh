#!/usr/bin/env bash
# Fetch top-N Project Gutenberg books as plain text.
#
# Env vars:
#   GUTENBERG_TOP_N  — number of books to fetch (100 / 500 / 2000 / 10000)
#
# Approach:
#   Gutenberg's "Top 100 EBooks yesterday/last 7 days/last 30 days" page lives at
#   https://www.gutenberg.org/browse/scores/top. For N > 100 we page through the
#   full "most-downloaded" list via the robot-friendly CSV catalog
#   (https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv) sorted by download
#   count — but Gutenberg doesn't publish per-book download counts in the CSV.
#   Our fallback for N > 100: scrape the top-100 page, then append IDs from the
#   "popular" browse pages for additional ranks.
#
# Each book is written to build/corpus/books/<id>-<slug>.txt. Idempotent.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

TOP_N="${GUTENBERG_TOP_N:-100}"
log "fetching top $TOP_N Gutenberg books into $BOOK_DIR"

# Produce a list of (id, slug) pairs for the top N books.
"$PY" - <<PY > /tmp/pergamon-gutenberg-list.tsv
import urllib.request, re, sys, html

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")

want = int("${TOP_N}")
pairs = []
seen = set()

# Top 100 (last 30 days) — most reliable list.
try:
    page = get("https://www.gutenberg.org/browse/scores/top")
except Exception as e:
    print("ERR failed to fetch top list:", e, file=sys.stderr)
    sys.exit(1)

# Links look like: <li><a href="/ebooks/1342">Pride and Prejudice ...</a> ...
pattern = re.compile(r'<li>\s*<a href="/ebooks/(\d+)">([^<]+)</a>')
for m in pattern.finditer(page):
    bid, title = m.group(1), html.unescape(m.group(2))
    if bid in seen:
        continue
    seen.add(bid)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]
    pairs.append((bid, slug))
    if len(pairs) >= want:
        break

# For N > 100, go through the "last 30 days" extended list and additional pages.
pages_to_try = [
    "https://www.gutenberg.org/ebooks/search/?sort_order=downloads",
]
page_no = 1
while len(pairs) < want and page_no <= 500:
    try:
        url = pages_to_try[0] + f"&start_index={1 + (page_no - 1) * 25}"
        page = get(url)
    except Exception:
        break
    found_this_page = 0
    for m in re.finditer(r'<a href="/ebooks/(\d+)"[^>]*>', page):
        bid = m.group(1)
        if bid in seen:
            continue
        seen.add(bid)
        pairs.append((bid, f"book{bid}"))
        found_this_page += 1
        if len(pairs) >= want:
            break
    if found_this_page == 0:
        break
    page_no += 1

for bid, slug in pairs[:want]:
    print(f"{bid}\t{slug}")
PY

count=0
while IFS=$'\t' read -r bid slug; do
  [[ -z "$bid" ]] && continue
  out="$BOOK_DIR/${bid}-${slug}.txt"
  if [[ -s "$out" ]]; then
    count=$((count + 1))
    continue
  fi
  # Gutenberg mirrors plain text at /files/<id>/<id>-0.txt (UTF-8) or /files/<id>/<id>.txt.
  for suffix in "-0" ""; do
    url="https://www.gutenberg.org/files/${bid}/${bid}${suffix}.txt"
    if curl -sL --fail --retry 2 --max-time 120 -o "$out" "$url"; then
      count=$((count + 1))
      break
    fi
    rm -f "$out"
  done
done < /tmp/pergamon-gutenberg-list.tsv

rm -f /tmp/pergamon-gutenberg-list.tsv

ok "gutenberg: $count books under $BOOK_DIR"
