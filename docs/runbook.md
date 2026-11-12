# Oracle runbook

How to use the oracle, in order of blast radius.

## Day one — build

```bash
git clone https://github.com/tchoffman/oracle.git ~/github/oracle
cd ~/github/oracle
make all
```

Then verify:

```bash
bin/oracle status
bin/oracle ask "how do I purify surface water?"
bin/oracle serve  # open http://localhost:8080 in a browser
```

## Daily use

- **Lookup**: `bin/oracle ask "..."` — RAG answer with sources
- **Browse**: `bin/oracle serve` then open `http://localhost:8080`, pick a ZIM, use its own search
- **Status**: `bin/oracle status` — what's installed, what's indexed, what's broken

## Adding content

### Add a ZIM

1. Append to `corpus/sources.yaml` under `zims:`
2. `make corpus` — downloads new, skips existing
3. `make serve` again — new ZIM is picked up automatically

### Add a PDF (survival manual, repair guide, etc.)

Two options:

**Option A — automated (public domain or direct URL):**
1. Append to `corpus/sources.yaml` under `pdfs:`
2. `make corpus && make index`

**Option B — manual (gated downloads or your own files):**
1. Drop the PDF into `build/corpus/pdfs/`
2. `make index`

The ingest script is idempotent — only new chunks are embedded.

## Off-grid use

### Before the lights go out (regularly)

- Run `make corpus` quarterly to refresh ZIMs (Wikipedia changes fast)
- Run `make models` after Ollama updates
- Verify `bin/oracle status` shows everything green

### When the lights go out

1. Boot the machine on inverter power
2. `bin/oracle ask "..."` works offline (no network needed)
3. `bin/oracle serve` for browse-the-wiki use

Nothing in the day-to-day loop talks to the internet, so **no additional steps** when going offline. That's the point.

### If the LLM is unusable (slow, confused, broken)

Fall back to:
- `bin/oracle serve` — pure wiki browse, no LLM in the loop
- Raw PDFs under `build/corpus/pdfs/` — open in Preview
- Printed cheatsheet (see `docs/quick-reference.md`) — triage, water, fire, splint

## Printed companion

Keep a printed copy of `docs/quick-reference.md` with the machine. If the oracle itself fails, that paper is the fallback for the first hour.
