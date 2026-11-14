# Getting started with Pergamon

A step-by-step walkthrough for your first install. Assumes you've never run
Pergamon before. Takes about 30 minutes end-to-end on a modern Mac, most of
which is downloads running in the background.

## What Pergamon is

An **offline reference machine** that combines:

- **A library** of wikis and books (Wikipedia, Wikivoyage, iFixit, survival
  manuals) you can browse without any internet.
- **A local LLM** (via [Ollama](https://ollama.com)) that answers questions
  by citing that library.
- **A set of services** you can optionally run alongside — calendar, ebook
  server, password vault, a Nostr relay for talking to other Pergamons.
- **A Nostr identity** so you can post classifieds, send DMs, and build
  reputation across other people's Pergamons (even over a mesh radio).

Everything runs on your own computer. Nothing leaves the LAN unless you
explicitly connect it to the wider Nostr network.

## Before you begin

You need:

- A **Mac** (Apple Silicon recommended). Linux works but the walkthrough
  hasn't been battle-tested there yet.
- **Homebrew** installed. If you don't have it: https://brew.sh.
- **Git** and **Python 3.11+** (both come free on modern macOS). Check with
  `python3 --version`.
- **Docker Desktop** — *only* if you want to run the services (calendar,
  ebook library, Nostr relay, password vault). You can skip Docker and still
  use the Pergamon library + ask/plan/search.
- **Disk space:**
  - Minimum install: ~2 GB
  - Default install: ~5 GB (fits a 16 GB Mac comfortably)
  - Comprehensive install: ~80 GB (for a dedicated appliance)
- **About 30 minutes** of attended time.

## Step 1 — Clone and set up

```bash
mkdir -p ~/github
cd ~/github
git clone https://github.com/tchoffman/pergamon.git
cd pergamon
```

## Step 2 — Pick what to install (interactive)

```bash
make setup
```

This walks you through:

1. **Pick a preset**: minimal, default, comprehensive, or custom.
2. **Model**: which LLM to use as the primary. Default is `llama3.1-8b-q4`
   (~5 GB, comfortable on a 16 GB Mac). On a bigger machine, pick `qwen2.5-14b-q4`
   for sharper answers.
3. **Embedding model**: how retrieval works. The default (`nomic-embed-text`)
   is fine for most people.
4. **Services** (optional): calendar, ebook library, password vault, Nostr
   relay. Pick none if you're only trying out the core RAG features.

This writes `config/install.local.yaml` with your picks. It's gitignored, so
it's yours alone and won't follow the repo around.

**Don't want to run setup?** Skip it. Everything below uses the `default`
preset, which is fine.

## Step 3 — Build the pergamon

```bash
make all
```

This runs in order:

1. **`make deps`** — installs Ollama + kiwix-serve via Homebrew (first run
   only; later runs are no-ops).
2. **`make venv`** — creates a Python environment under `build/venv`.
3. **`make models`** — pulls your chosen LLM + embedding model via Ollama.
   This is the big one — depending on model size, 3-10 GB download.
4. **`make corpus`** — downloads the ZIMs + public-domain PDFs you picked
   during setup. Default preset is ~4.7 GB; `kiwix.org` is sometimes slow
   so this may take a while.
5. **`make index`** — chunks + embeds any PDFs into the Chroma vector store
   so `pergamon ask` can cite them.

You can walk away during this. If any step fails (bad network, Ollama
hiccup), just re-run `make all` — every step is idempotent.

## Step 4 — Ask the pergamon something

```bash
bin/pergamon ask "how do I purify surface water?"
```

You should see:
- A streamed answer from the LLM
- A **Sources** section listing where the answer came from (will be slim at
  first — more on this below)

## Step 5 — Check what you have

```bash
bin/pergamon status
```

Shows a table with the Ollama binary, kiwix-serve binary, models, the
corpus files on disk, and the number of chunks in the RAG index.

## Step 6 — Index your ZIM content (optional, slow, big win)

Out of the box, your 4.7 GB of ZIM content is **browse-only**. To make
`ask` grounded in that content, run:

```bash
make zim-index
```

Expect several hours for a full iFixit ingest. To smoke-test first:

```bash
ZIM_LIMIT=50 make zim-index
```

That ingests 50 articles per ZIM so you can verify the pipeline works
before committing to the long run.

After indexing, re-ask: `bin/pergamon ask "fix my refrigerator"` — the
answer should cite actual iFixit articles with clickable kiwix URLs.

## Step 7 — Browse the library

The `kiwix-serve` binary may not have finished downloading (its CDN is
unreliable); if so, `make deps` falls back to installing **Kiwix.app** (the
macOS GUI).

```bash
bin/pergamon serve
```

- If the headless binary is there: opens a browser at `http://localhost:8080`
  with search across all your ZIMs.
- If only the GUI is there: launches Kiwix.app with your ZIMs preloaded.

Either way you can type a term and search across every indexed article.

## Step 8 — Use the web UI

```bash
make web
```

Opens the Pergamon browser UI at `http://localhost:8090`. Features:

- **Ask / Plan / Search** mode selector
  - *Ask* — streams a RAG answer with citations
  - *Plan* — structured plan output (Goal / Steps / Resources / Risks /
    Verification)
  - *Search* — top-K raw retrieval hits, no LLM involved
- **Identity** link in the header → manage your Nostr keys (step 9)
- Phone-friendly — point any device on the LAN at
  `http://<pergamon-mac-ip>:8090`

## Step 9 — Create your Nostr identity

Pergamon's cross-machine features (classifieds, distributed posts, DMs)
are built on the [Nostr protocol](https://nostr.com). Each user has a
keypair — the *private key* (`nsec1...`) is your account; the *public key*
(`npub1...`) is your handle.

```bash
bin/pergamon identity create trenton --nip05 trenton@pergamon.local --display "Trenton"
```

This:
- Generates a secp256k1 keypair
- Saves the private key at `build/identity/trenton.key` (mode 0600)
- Marks it as the active identity
- Prints your `npub` (safe to share)

**Back it up:**

```bash
bin/pergamon identity export trenton --path ~/safe/trenton.nsec
```

Put that file on an offline USB drive. If you lose it and the machine
dies, you lose the identity.

See [identity.md](identity.md) for the full command reference and recovery
procedures.

## Step 10 — (Optional) Start the services

If you installed Docker Desktop and picked services during `make setup`:

```bash
bin/pergamon services list        # see what's enabled
bin/pergamon services up          # start them
bin/pergamon services status      # check containers
```

What you get, per the default services pack:

| Service | URL | What |
|---|---|---|
| Calendar | http://localhost:5232 | CalDAV/CardDAV; set phones to sync here |
| Ebook library | http://localhost:8083 | Calibre-Web; Send-to-Kindle over WiFi |
| Password vault | http://localhost:8089 | Vaultwarden, Bitwarden-compatible |
| Nostr relay | ws://localhost:8091 | Point any Nostr client here |

Each has its own README under `services/<id>/README.md` with first-time
setup. **Each is LAN-only by default** — nothing is exposed to the
internet.

## Step 11 — Post your first classified

With a Nostr identity and the relay running:

```bash
bin/pergamon classified post \
    --title "20 lb apples" \
    --price-oz-ag 0.3 \
    --accepts silver,barter \
    -t apples -t harvest \
    "Honeycrisp, pick up in Asheville"
```

Browse your own classifieds:

```bash
bin/pergamon classified list
bin/pergamon classified search apples
```

To share with other Pergamons: they add your relay URL to theirs
(`bin/pergamon nostr relays add ws://your-ip:8091`) and vice versa.

## Daily use

Day to day, you'll mostly use these four:

```bash
bin/pergamon ask "..."         # answers with sources
bin/pergamon plan "..."        # structured plan output
bin/pergamon search "..."      # raw retrieval, no LLM
bin/pergamon serve             # browse wikis in Kiwix
```

Or the web UI (`make web`) for the same thing in a browser you can point
phones at.

## Troubleshooting

**`make all` fails with "ollama: command not found"** → Homebrew install
failed. Run `brew install ollama` manually, then `make all` again.

**Ollama pull is incredibly slow** → not a Pergamon issue; Ollama's CDN
is occasionally regional. Try later or point `OLLAMA_HOST` at a local
mirror.

**Corpus download fails on kiwix.org** → their CDN is spotty. The fetch
script resumes partial downloads, so just re-run `make corpus`.

**`pergamon ask` cites wrong/random sources** → the RAG index is empty or
too small. Run `make zim-index` (slow) to actually ingest your ZIM
content. Until then, the LLM is answering mostly from general knowledge
and grabbing weak semantic matches for citations.

**Web UI returns 500 on /** → check `make test` passes; if you edited
templates, you may have broken Jinja. Nostr identity page is at
`/identity`; profile publish writes to the configured relays and reports
per-relay status in the JSON response.

**Docker services won't start** → make sure Docker Desktop is running
(the whale icon in the menu bar). `docker ps` should work.

## What's not working yet

Live-tracked at: https://github.com/tchoffman/pergamon/issues

Known limits as of this writing:

- The Meshtastic radio path is skeleton-only — the mock mode works, the
  real-radio path has not been verified against hardware.
- The `kiwix-serve` headless binary sometimes fails to download from
  kiwix.org; fallback to Kiwix.app is automatic.
- ZIM ingestion is slow (local Ollama embedding is ~5 chunks/sec on an
  M4). Full iFixit is several hours; full Wikipedia Simple is longer.
- Services don't have a reverse proxy yet — each is at a raw port
  (issue #6). `pergamon.local` style hostnames require manual
  `/etc/hosts` entries for now.

## Where to go next

- **Daily reference**: [commands.md](commands.md) — every subcommand with
  flags and examples.
- **Identity details**: [identity.md](identity.md) — NIP-05, backup,
  recovery, multi-user households.
- **Hardware planning**: [hardware.md](hardware.md) — the "cage machine"
  for long-term off-grid use.
- **Printable survival cheatsheet**: [quick-reference.md](quick-reference.md) —
  water, fire, triage; print and keep with the machine.
- **Ideas backlog**: [ideas.md](ideas.md) — what's planned but not built.
- **GitHub issues**: open and close as you build and discover bugs.
