# Pergamon

An offline reference machine for extended off-grid scenarios. Combines large knowledge bases (Wikipedia, survival manuals, repair guides, OpenStreetMap, etc.) with a locally-running LLM so you can **research, plan, and look things up without any internet**.

Named after the [ancient library of Pergamon](https://en.wikipedia.org/wiki/Library_of_Pergamum) — Alexandria's rival, famous for parchment and for surviving when other collections burned.

This repo is the **recipe**, not the appliance. Running the scripts on a fresh machine produces a working Pergamon: models pulled, corpus downloaded, RAG index built, servers ready. The actual knowledge/models are gitignored and live in `build/` locally.

## Design

```
┌─ GitHub (this repo) ──────────────┐    ┌─ Local machine (your Pergamon) ─┐
│ scripts/     — build recipe        │ ─> │ build/models/    — Ollama blobs │
│ bin/         — CLI tools          │    │ build/corpus/    — ZIMs + PDFs  │
│ rag/         — Python package     │    │ build/chroma/    — vector DB    │
│ Makefile     — orchestration      │    │ (gitignored, portable)          │
└───────────────────────────────────┘    └─────────────────────────────────┘
```

## Quick start (on a fresh Mac)

```bash
git clone https://github.com/tchoffman/pergamon.git
cd pergamon
make setup        # (optional) pick what to install interactively
make all          # install deps → pull models → fetch corpus → build index
bin/pergamon ask "how do I purify surface water?"
bin/pergamon serve  # browse ZIMs at http://localhost:8080
```

Skip `make setup` and `make all` uses the **default** preset (~5 GB, fits a 16 GB Mac). Other presets live in `config/presets/`:

| Preset | Size | What |
|---|---|---|
| **minimal** | ~1 GB | Wikipedia Simple + survival PDFs. Barebones. |
| **default** | ~5 GB | + Wikivoyage, Wiktionary, iFixit, SE dumps, top-100 Gutenberg. |
| **comprehensive** | ~80 GB | Full English Wikipedia, Khan Academy core, wide SE dumps, mirrored docs sites. Cage-class disk. |

`make setup` writes `config/install.local.yaml` (gitignored) — you can also edit it by hand. `make plan` shows what would be fetched without downloading. `make all` is idempotent — re-running only does work that's missing. See `make help`.

## Documentation

- **[docs/getting-started.md](docs/getting-started.md)** — step-by-step walkthrough for first-time install. Start here if this is your first time.
- **[docs/commands.md](docs/commands.md)** — every subcommand and its flags, as a reference.
- **[docs/identity.md](docs/identity.md)** — Nostr keys, NIP-05, backup + recovery.
- **[docs/hardware.md](docs/hardware.md)** — dev-box vs cage-machine planning.
- **[docs/runbook.md](docs/runbook.md)** — how to use Pergamon day-to-day and off-grid.
- **[docs/quick-reference.md](docs/quick-reference.md)** — printable survival cheatsheet to keep with the machine.
- **[docs/ideas.md](docs/ideas.md)** — backlog of features not yet built.
- **[docs/roadmap.md](docs/roadmap.md)** — the three planned modules (comms, services, compendium).

## What's inside the "app"

| Component       | Purpose                                             | Tool                  |
|-----------------|-----------------------------------------------------|-----------------------|
| LLM runtime     | Local inference, Metal-accelerated on Apple Silicon | [Ollama](https://ollama.com) |
| Primary model   | General Q&A + RAG synthesis                         | `llama3.1:8b-instruct-q4_K_M` |
| Embedding model | Semantic search over corpus                         | `nomic-embed-text`    |
| Vector store    | Retrieves relevant passages for RAG                 | [Chroma](https://www.trychroma.com) |
| Offline wikis   | Wikipedia, iFixit, etc. (ZIM format)                | [kiwix-serve](https://kiwix.org) |
| CLI             | `pergamon ask`, `pergamon serve`, `pergamon status` | Python + bash         |

## Hardware

Dev target: M4 MacBook Air, 16GB RAM, ~80GB free disk. See [docs/hardware.md](docs/hardware.md) for the long-term "cage machine" recommendations and faraday considerations.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for planned modules:

- **Comms** — radio / Meshtastic / Reticulum integration so pergamons can talk to each other without internet
- **Survival compendium** — a curated, deeper offline library (medical, food, repair, agriculture, …)
- **In-home services** — calendar, photos, notes, media, home automation hosted on the same box

## Why "Pergamon"?

A library that survives when the rest doesn't. Lots of inputs, synthesized answers, trusted when the regular channels are down.
