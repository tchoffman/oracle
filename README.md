# Oracle

An offline reference machine for extended off-grid scenarios. Combines large knowledge bases (Wikipedia, survival manuals, repair guides, OpenStreetMap, etc.) with a locally-running LLM so you can **research, plan, and look things up without any internet**.

This repo is the **recipe**, not the appliance. Running the scripts on a fresh machine produces a working oracle: models pulled, corpus downloaded, RAG index built, servers ready. The actual knowledge/models are gitignored and live in `build/` locally.

## Design

```
┌─ GitHub (this repo) ──────────────┐    ┌─ Local machine (the oracle) ────┐
│ scripts/     — build recipe        │ ─> │ build/models/    — Ollama blobs │
│ bin/         — CLI tools          │    │ build/corpus/    — ZIMs + PDFs  │
│ rag/         — Python package     │    │ build/chroma/    — vector DB    │
│ Makefile     — orchestration      │    │ (gitignored, portable)          │
└───────────────────────────────────┘    └─────────────────────────────────┘
```

## Quick start (on a fresh Mac)

```bash
git clone https://github.com/tchoffman/oracle.git
cd oracle
make all          # install deps → pull models → fetch corpus → build index
oracle ask "how do I purify surface water?"
oracle serve      # browse ZIMs at http://localhost:8080
```

`make all` is idempotent — re-running only does work that's missing. See `make help`.

## What's inside the "app"

| Component       | Purpose                                             | Tool                  |
|-----------------|-----------------------------------------------------|-----------------------|
| LLM runtime     | Local inference, Metal-accelerated on Apple Silicon | [Ollama](https://ollama.com) |
| Primary model   | General Q&A + RAG synthesis                         | `llama3.1:8b-instruct-q4_K_M` |
| Embedding model | Semantic search over corpus                         | `nomic-embed-text`    |
| Vector store    | Retrieves relevant passages for RAG                 | [Chroma](https://www.trychroma.com) |
| Offline wikis   | Wikipedia, iFixit, WikiHow, etc. (ZIM format)       | [kiwix-serve](https://kiwix.org) |
| CLI             | `oracle ask`, `oracle serve`, `oracle status`       | Python + bash         |

## Hardware

Dev target: M4 MacBook Air, 16GB RAM, ~80GB free disk. See [docs/hardware.md](docs/hardware.md) for the long-term "cage machine" recommendations and faraday considerations.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for planned modules:

- **Comms** — radio / Meshtastic / Reticulum integration so oracles can talk to each other without internet
- **Survival compendium** — a curated, deeper offline library (medical, food, repair, agriculture, …)
- **In-home services** — calendar, photos, notes, media, home automation hosted on the same box

## Why "oracle"?

An oracle machine: lots of inputs, synthesized answers, trusted when the regular channels are down.
