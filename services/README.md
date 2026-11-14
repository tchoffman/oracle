# Services

LAN-only self-hosted services that run alongside the core pergamon.

**Status:** skeleton. Compose files + READMEs are in place for four
services. The `pergamon services` CLI dispatcher, install-config
integration, and setup-TUI wiring are **not yet implemented** — for now,
start services by hand:

```bash
cd services/radicale && docker compose up -d
cd services/calibre-web && docker compose up -d
cd services/vaultwarden && VW_ADMIN_TOKEN="$(openssl rand -base64 48)" docker compose up -d
cd services/nostr-relay && docker compose up -d
```

## Available services

| id | title | port | purpose |
|---|---|---|---|
| radicale | Calendar + Contacts | 5232 | CalDAV/CardDAV, syncs to phones over LAN |
| calibre-web | E-reader library | 8083 | Serves ebooks to Kindle/phones, Send-to-Kindle |
| vaultwarden | Password vault | 8089 | Bitwarden-compatible, LAN-only |
| nostr-relay | Nostr relay | 8091 | Backbone for distributed social/DM/marketplace |

Each has its own `docker-compose.yml` + `README.md` with setup specifics.

## Dependencies

- Docker Engine or Docker Desktop
- `docker compose` v2 (already included in Docker Desktop)

## Data

Every service writes to `../build/services/<id>/`, which is gitignored.
Back up this directory to offline media — losing it means losing your
calendars, passwords, Nostr history, etc.

## What's next

Still to wire (tracked in `docs/ideas.md` → Foundations):

- `services/catalog.yaml` already exists — the CLI dispatcher reads this
- `pergamon services {list,up,down,status,logs}` CLI
- `rag/install_config.py` loads `services:` from install.local.yaml
- Setup TUI asks which services to enable
- Unit tests for the catalog parser
- Optional: Caddy reverse proxy so services get friendly `.local` hostnames
  instead of raw ports
