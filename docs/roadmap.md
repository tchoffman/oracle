# Roadmap

What's shipped today vs what's next. Each numbered module below is self-contained; order is rough priority.

## Shipped (v0.1)

- `make all` builds a working pergamon on a fresh Mac: Ollama + kiwix-serve + Chroma + RAG.
- `pergamon ask "..."` answers questions with citations from the indexed PDF corpus.
- `pergamon serve` exposes the ZIM collection at `http://localhost:8080`.
- Starter corpus: Simple English Wikipedia, Wikivoyage, WikiHow, iFixit, FM 21-76, Hesperian medical references.
- Docs: hardware (cage machine), runbook, printable quick-reference.

## Module 1 — Radio & mesh comms

**Goal:** when there's no internet, the pergamon can still (a) receive outside info and (b) collaborate with other radio-connected pergamons.

Three layers of "no internet":
- **Shortwave / HF receive-only** — news, weather, time signals. No license needed for listening.
- **Ham (VHF/UHF simplex, HF digital)** — slow but global. Licensed operator required for TX.
- **Mesh (Meshtastic / Reticulum / Meshcore)** — short-range (1–10 km LoRa), decentralized, license-free.

### Planned pieces

| Piece | Hardware | Role |
|-------|----------|------|
| Shortwave bridge | Tecsun PL-330 + mic-to-USB cable, or RTL-SDR dongle | Timed cron captures of specific broadcasts; transcribe with Whisper; index like a PDF |
| Meshtastic node | Heltec V3 or RAK WisBlock | Pergamon publishes digests over LoRa; subscribers run their own pergamons and merge updates |
| Reticulum stack | RNode / RNS over LoRa, packet radio, or TCP | More robust alternative to Meshtastic — supports larger payloads, end-to-end encryption, store-and-forward |
| APRS gateway | TNC-Pi or Direwolf + Baofeng cable | Send location beacons, short messages; receive weather reports |
| Collaboration protocol | Signed deltas of RAG index (small). Peer pergamons exchange & verify. | Scales knowledge across a small group without internet |

### Rough design for pergamon-to-pergamon sync

```
pergamon A ──┐  (LoRa mesh, ~250 kbps burst, ~10 kbps sustained)
            ├─► signed delta packets (new PDFs, new ZIM highlights, incident reports)
pergamon B ──┘  
           └─► each peer verifies signature, merges deltas into local Chroma
```

A "delta" is small: a compact manifest + embeddings + source URL. Full bulk transfer happens over sneakernet (SD cards). Mesh is for metadata and pointers.

### First step

Prototype a Meshtastic-only build: ship a `modules/comms/meshtastic/` Python module that lets the pergamon receive queries from mesh and reply with short summaries (chunked over multiple LoRa packets). Keep it isolated and feature-flagged — the core pergamon works without it.

## Module 2 — Survival compendium

A curated, deeper library beyond today's starter PDFs. Open-license where possible.

### Core shelves

- **Medical**: *Where There Is No Doctor*, *WTIN Dentist*, *WTIN Midwife*, *WHO Wound Care*, *Ship Captain's Medical Guide*, Army 68W handbook
- **Food**: Encyclopedia of Country Living (Emery), Carla Emery, Peterson field guides (edible plants), USDA food preservation handbook, John Seymour's *Self-Sufficient Life*
- **Water**: CDC drinking-water guidance, well drilling manuals, Berkey/Sawyer whitepapers
- **Shelter/building**: *A Pattern Language* (Alexander), *Shelter* (Kahn), timber-framing + strawbale + cordwood manuals, FEMA shelter designs
- **Energy**: off-grid solar design handbooks, battery chemistry refs, wood gasifier plans
- **Repair**: iFixit full dump, Haynes/Chilton for owned vehicles, Machinery's Handbook, Reader's Digest *Complete Do-It-Yourself Manual*
- **Comms**: ARRL Handbook (yearly), ARRL Antenna Book, NTIA freq allocation tables
- **Agriculture**: *One-Straw Revolution*, *The Market Gardener* (Fortier), local extension-service manuals, seed-saving guides (Seed to Seed)
- **Veterinary**: Merck Veterinary Manual
- **Reference**: CRC Handbook of Chemistry and Physics, Machinery's Handbook, Grey's Anatomy (public domain), military FMs (21-76, 3-05.70, 4-25.11)
- **Classics / morale**: Gutenberg top-2000 + a few modern public-domain fiction curations

### Acquisition sources

- [Project Gutenberg](https://www.gutenberg.org/) — classics, out-of-copyright reference
- [Standard Ebooks](https://standardebooks.org/) — well-formatted PG derivatives
- [Internet Archive](https://archive.org/) — military FMs, public-domain gov publications
- [Hesperian](https://hesperian.org/) — medical, CC-licensed
- [Low-Tech Magazine](https://www.lowtechmagazine.com/) — practical appropriate-tech articles
- [Appropedia](https://www.appropedia.org/) — DIY sustainability wiki (ZIM available)
- [PrePrint commons](https://arxiv.org/) — research papers (heavy; targeted downloads only)
- Local extension services (free PDFs, state-specific)

### Planned: `corpus/compendium.yaml`

Mirror `corpus/sources.yaml`'s structure, but bigger and organized by shelf. Separate so people can pick shelves rather than "all or nothing."

## Module 3 — In-home server services

Treat the pergamon machine as a quiet in-home services host. If it's running anyway, give it more jobs.

### Candidates

| Service | Purpose | Notes |
|---------|---------|-------|
| **Calendar / CalDAV** (Radicale) | Shared family calendar that works offline | Syncs to phones over LAN |
| **Contacts / CardDAV** (Radicale) | Address book that doesn't live in cloud | Same server as calendar |
| **Notes / sync** (Trilium, Obsidian LiveSync, SilverBullet) | Shared markdown knowledge base | Trenton already uses Obsidian; wire this up to the existing `tchoffman/vault` |
| **Photos** (Immich or PhotoPrism) | Self-hosted photo library | Family memories without cloud |
| **Media** (Jellyfin) | Movies, shows, music | Especially useful off-grid for morale |
| **Reading** (Kavita or Calibre-Web) | Serves the ebook collection to Kindle/Kobo/phones | Direct complement to the survival compendium |
| **Games** (nothing-net or custom) | Family offline games, puzzles, educational | Include a couple public-domain classics |
| **Home automation** (Home Assistant) | Local-first smart home | No cloud dependence; pairs well with solar monitoring |
| **DNS/ad-block** (Pi-hole / Blocky) | Clean DNS for the house | Low resource cost |
| **Dashboards** (Grafana + node_exporter) | Solar / battery / disk / temp monitoring | Powers the "is the pergamon healthy?" view |

### Deployment approach

- Each service lives in `services/<name>/docker-compose.yml`
- Top-level `docker-compose.yml` composes anything enabled
- `make services-up` / `make services-down`
- Reverse proxy via Caddy on a `.pergamon.local` mDNS name

Deliberately **modular** — the LLM + RAG core doesn't depend on any of this. If you don't want calendars, don't enable them.

### Interesting cross-cutting idea

The RAG index can ingest from these services:
- Your calendar's past entries become "what was I doing last March"
- Your notes become searchable
- Your photos' metadata becomes queryable ("show me pictures from the hike in 2024")

Opt-in, local-only — the LLM can ground answers in *your* life, not just Wikipedia.

## Open questions

- Should the pergamon have a lightweight web UI (not just CLI)? Small FastAPI frontend would make it browsable on phones over LAN.
- How to structure corpus manifest so a shelf can be selected on install? (`make corpus SHELF=medical,repair`)
- Model management: do we need a "slim profile" (3B) vs "default" (8B) vs "cage" (32B+) toggle in Makefile?
