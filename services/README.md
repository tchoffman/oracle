# Services

LAN-only self-hosted services that run alongside the core pergamon.

Enable services via `pergamon setup` (TUI picker) or by hand-editing
`config/install.local.yaml` under a `services:` key. Then:

```bash
pergamon services list            # show catalog + enabled state
pergamon services up              # start all enabled services
pergamon services up radicale     # or just one
pergamon services status          # container health
pergamon services logs radicale -f
pergamon services down            # stop all
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

The `pergamon services` CLI checks for both and fails fast with a clear
message if missing.

## Data

Every service writes to `../build/services/<id>/`, which is gitignored.
Back up this directory to offline media — losing it means losing your
calendars, passwords, Nostr history, etc.

## What's next

Still open (tracked in `docs/ideas.md`):

- Caddy reverse proxy so services get friendly `.local` hostnames
  (`calendar.pergamon.local`) instead of raw ports
- Additional services: Jellyfin (media), Immich (photos), Home Assistant,
  Vaultwarden backups, Grafana dashboards
- First real app on Nostr: the classifieds marketplace
