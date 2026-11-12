# Module 3 — In-home services

**Status:** planning. See [../docs/roadmap.md](../docs/roadmap.md).

Treat the pergamon machine as a house services host: calendar, photos, notes, media, home automation. Each service is self-contained; enable only what you want.

## Planned layout

```
services/
├── docker-compose.yml       # top-level composer (enable with env flags)
├── calendar/                # Radicale (CalDAV + CardDAV)
├── notes/                   # Trilium or SilverBullet, syncing with existing Obsidian vault
├── photos/                  # Immich — self-hosted photo library
├── media/                   # Jellyfin
├── books/                   # Kavita or Calibre-Web — serves the survival compendium
├── home-automation/         # Home Assistant
├── dns/                     # Blocky — ad-blocking + local DNS
└── monitoring/              # Grafana + node_exporter for solar/battery/disk
```

## Selection principles

- **LAN-only by default.** Nothing exposed to the public internet unless the user asks.
- **Local-first.** No cloud dependencies; services must survive weeks offline.
- **Low idle footprint.** A quiet Mac mini must still run them all without fans spinning up.
- **Backup-friendly.** Volume layout makes it easy to snapshot the whole services state.

## Idea: RAG over your own data

The pergamon's RAG index can ingest from these services so you can ask:
- "what was that kayak trip we took in 2024?" → pulls from photos + calendar
- "what did I decide about the greenhouse last spring?" → pulls from notes
- "which of my tools has an iFixit guide?" → cross-references inventory notes with iFixit ZIM

Opt-in per-service. Lives local; never leaves the house.
