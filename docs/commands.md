# Command reference

Every `pergamon` subcommand with its flags. For the first-time
walkthrough, see [getting-started.md](getting-started.md).

## Build + lifecycle (Makefile)

```bash
make help            # one-line help per target
make setup           # interactive install picker → writes install.local.yaml
make plan            # dry-run: show what `make corpus` would download
make all             # full build: deps → venv → models → corpus → index
make deps            # install Ollama + kiwix-serve (idempotent)
make venv            # Python venv under build/venv
make models          # pull LLM + embedding model via Ollama
make corpus          # download ZIMs + public-domain PDFs per install config
make index           # embed PDFs into Chroma (uses active embedding model)
make zim-index       # embed ZIM articles into Chroma (slow; ZIM_LIMIT=N caps)
make status          # pergamon status (deps, models, corpus, index)
make serve           # launch kiwix-serve or Kiwix.app with your ZIMs
make web             # launch the web UI at :8090
make test            # pytest unit suite (no network)
make check-urls      # HEAD-check every URL in the plan (slow; needs network)
make smoke-test      # end-to-end: deps/models/corpus/index/ask
make clean           # wipe build/ (redownload everything)
```

## Core: ask / plan / search

```bash
pergamon ask "question"
#   Streams a RAG answer. Retrieves top-K chunks, feeds to the LLM with
#   citations. Prints Sources at the end — each cites the ZIM article URL
#   (if applicable) and chunk index.

pergamon plan "goal"
#   Same retrieval but with a planner-tuned system prompt. Output is
#   structured markdown: Goal / Steps / Resources / Risks & mitigations
#   / Verification.

pergamon search "query" [--k N]
#   Raw semantic search — top-K chunks with sources + previews. No LLM.
#   Default K is 6; override with --k.
```

## Browse the library

```bash
pergamon serve [--port N] [--app]
#   Default port 8080. Prefers headless kiwix-serve binary; if missing
#   AND Kiwix.app is installed, falls back to opening the GUI with your
#   ZIMs pre-loaded. --app forces GUI mode.

pergamon web [--port N] [--host 0.0.0.0]
#   Web UI at :8090 by default. Ask / Plan / Search in a browser, plus
#   /identity, /.well-known/nostr.json, etc.
```

## Status + admin

```bash
pergamon status      # Rich table: binaries, models, ZIMs, PDFs, Chroma count
pergamon shell       # Drop into a Python REPL with the venv activated
pergamon setup       # Interactive install picker
```

## Identity (Nostr keys)

See [identity.md](identity.md) for background.

```bash
pergamon identity list
#   Table of all identities on this machine + which is active.

pergamon identity create <name> [--nip05 user@domain] [--display "Name"]
#   Generate a new keypair; mark it active. --nip05 is optional but useful
#   for human-readable handles.

pergamon identity use <name>
#   Switch the active identity. All subsequent signing (ask doesn't sign,
#   but nostr/classified/delegation do) uses this one.

pergamon identity show [<name>] [--reveal]
#   Show public info. --reveal ALSO prints the nsec (be sure no one's
#   looking over your shoulder).

pergamon identity export <name> [--path FILE]
#   Export the nsec. Default prints to stdout; --path writes a 0600 file.
#   Put it on a USB drive; if the machine dies, this is your recovery.

pergamon identity import <name> <file>
#   Create an identity from an exported nsec. Useful for restoring or
#   moving between machines.

pergamon identity delete <name>
#   Removes the key file + metadata. Prompts for confirmation.
```

## Nostr publishing

```bash
pergamon nostr post "content"  [--kind N]  [-t tagname,value ...]
#   Sign with the active identity, publish to all configured relays.
#   Default kind is 1 (short note).

pergamon nostr relays            # list configured relays
pergamon nostr relays add ws://peer.example/
pergamon nostr relays rm  ws://peer.example/
```

## Classifieds

```bash
pergamon classified post \
    --title "20 lb apples" \
    [--price-oz-ag 0.3] [--price-usd 12.50] \
    [--accepts silver,barter,labor] \
    [--location "Asheville NC"] \
    [-t apples -t harvest] \
    "description text..."
#   Kind 30402 addressable event per NIP-99 with Pergamon's price tag
#   extensions. Signs with the active identity, publishes to all
#   configured relays.

pergamon classified list [--tag X] [--limit 50]
#   Fetch classifieds from relays. --tag filters by hashtag.

pergamon classified search "chicken"
#   Client-side substring filter across title/description/location.
```

## Delegation (NIP-26)

```bash
pergamon delegation create --to <npub> [--kind N]+ [--until 30d]
#   Sign a delegation authorizing <npub> to post specific kinds on your
#   behalf for the window. --until accepts: 7d / 24h / ISO date / unix.
#   Outputs the delegation tag; share with the delegatee who attaches it
#   to events.

pergamon delegation verify <delegator_hex> <delegatee_hex> <conditions> <sig>
#   Verify a delegation signature.
```

## Mesh (Meshtastic)

```bash
pergamon mesh mock
#   Dev mode: stdin → chunked LoRa-formatted RAG answer. No radio needed.

pergamon mesh listen
#   Production: opens serial interface to a USB-attached Meshtastic node.
#   Subscribes to DMs; replies with chunked RAG answers.
#   Honors config/install.local.yaml → comms.meshtastic.allowed_node_ids.
```

## Ledger (generic records)

```bash
pergamon ledger list
#   Show available ledgers (defined in config/ledgers/*.yaml).

pergamon ledger show <name> [filters...]
#   Print all rows (or filtered) as a table. Filter forms: k=v, k~sub, k<N,
#   k>N, k<=N, k>=N.

pergamon ledger add <name> field=value [...]
#   Insert a row. Date fields accept ISO (2027-01-15), bool fields accept
#   yes/no/true/false/1/0, enums must match declared options.

pergamon ledger rm <name> <id>
#   Delete a row by its integer id.

pergamon ledger query <name> field=value [...]
#   Alias of show with filters.
```

## Services (Docker)

Requires Docker Desktop. Each service lives under `services/<id>/` with
its own `docker-compose.yml` + README.

```bash
pergamon services list                   # catalog + enabled state (on/off)
pergamon services up [id ...]            # start enabled (or named) services
pergamon services down [id ...]          # stop
pergamon services restart [id ...]       # restart
pergamon services status                 # docker ps filtered to pergamon-*
pergamon services logs <id> [-f]         # tail one service's logs
```

Services shipped today:

| id | title | port | what |
|---|---|---|---|
| radicale | Calendar + Contacts | 5232 | CalDAV/CardDAV |
| calibre-web | E-reader library | 8083 | Ebooks + Send-to-Kindle |
| vaultwarden | Password vault | 8089 | Bitwarden-compatible |
| nostr-relay | Nostr relay | 8091 | WebSocket; backbone for classifieds + DMs |

Each service's `README.md` has its own first-time-setup walkthrough.

## Config files cheat sheet

| Path | What | Edit by hand? |
|---|---|---|
| `config/catalog.yaml` | Catalog of available corpus items + models | No, the committed source |
| `config/presets/*.yaml` | Named install profiles | No, committed |
| `config/install.yaml` | Which preset is the default | Rarely |
| `config/install.local.yaml` | **Your** install picks | Yes (or via `pergamon setup`) |
| `services/catalog.yaml` | Available services | No, committed |
| `config/ledgers/*.yaml` | Ledger schemas | Yes — add new ledgers here |
| `rag/config.yaml` | RAG defaults (chunk size, retrieval K, etc.) | Rarely |

## Environment variables worth knowing

| Var | Default | What |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Point at a different Ollama instance |
| `ZIM_LIMIT` | unlimited | Cap articles per ZIM in `make zim-index` |
| `VW_ADMIN_TOKEN` | unset | Vaultwarden admin panel token at service startup |
| `MESHTASTIC_PORT` | auto-detect | Override USB device for `pergamon mesh listen` |
| `DRY_RUN=1` | — | `scripts/fetch-corpus.sh` prints the plan but doesn't fetch |
