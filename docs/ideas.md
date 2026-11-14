# Pergamon ideas backlog

The running list of features we've discussed but not yet built. Organized by
category; ★ marks the ones worth building soon; ⚡ flags the three foundational
primitives most other features build on.

See [roadmap.md](roadmap.md) for the three modules already scaffolded (comms,
services, compendium).

---

## Foundations (do these first — everything else is cheaper afterwards)

- **⚡ Model selection in setup** — pick primary + embedding model. Catalog
  the options with sizes + notes. Warn that changing embedding model requires
  reindex. (Shipping now.)

- **⚡ Ledger primitive** — SQLite-backed record keeping with YAML-defined
  schemas. One engine; food/seed/maintenance/medical/journal ledgers become
  config files, not new code. (Shipping now.)

- **⚡ Nostr relay on each pergamon** — enables social, email-ish messaging,
  weather sharing, marketplace, mesh addressing. Single protocol unlocks the
  entire "cross-machine apps" column.

- **Services skeleton** — top-level `docker-compose.yml` with a reverse proxy
  (Caddy) under `pergamon.local`. Every local app plugs in here.

---

## Local apps (one machine)

- **★ Calendar** — Radicale (CalDAV + CardDAV). Syncs to phones over LAN.
- **★ Recipe book** — two flavors: (a) curated collection ingested into RAG
  (Fannie Farmer, Hesperian's nutrition books, USDA preservation); (b) personal
  recipe book as a ledger instance. Natural LLM pairing: "what can I cook
  tonight?" × food inventory.
- **Ereader library** — Calibre-Web. Handles Kindle Send-To-Kindle over local
  WiFi. Trivial to add.
- **Password manager** — Vaultwarden (Bitwarden-compatible). One of the
  most-missed services off-grid.
- **Document vault** — titles, licenses, passports, deeds. Encrypted at rest;
  printable QR recovery.
- **Media library** — Jellyfin. Movies, shows, music. For morale.
- **Games** — curated public-domain classics in a browser: chess, go,
  backgammon, cribbage, Tetris clone, a roguelike. Skip anything with licensing
  friction.
- **Home automation** — Home Assistant. Local-first; integrates with solar
  monitors, door sensors, etc.
- **Dashboards** — Grafana + node_exporter for solar / battery / disk / temp.

## Cross-machine apps (Nostr-based)

- **Distributed social / message board** — Nostr kind 1 (short notes) + kind
  34550 (communities). A "pergamon circle" is a relay you're on.
- **Email-like messaging** — Nostr kind 4 (DMs). Not real email; not
  interoperable with SMTP. But works mesh + internet transparently.
- **Weather** — a pergamon with a sensor (or an RTL-SDR + NOAA Weather Radio
  decode) publishes readings; others subscribe.
- **★ Food / goods classifieds** — "I have 20 lbs of apples" / "need 1 lb of
  coffee". Publish-browse only; no payment layer. Trust is social.
- **News digest** — a pergamon with internet pulls headlines, publishes as a
  Nostr event, offline peers consume it.
- **Mesh pergamon directory** — short names → node addresses via gossiping
  relays.

## Household / family

- **★ Food inventory** — ledger instance. Barcode scan via phone PWA (Web
  Barcode Detection). OpenFoodFacts has 2M+ product entries freely downloadable
  for offline barcode-to-name lookup. Expiry alerts. Cross with recipe book.
- **Seed library** — ledger. Germination dates, save-from lineage, where
  planted, source.
- **Workshop / maintenance log** — ledger. Vehicle, generator, well pump
  service intervals. Pairs with iFixit.
- **Household journal** — markdown daily log, auto-indexed into RAG.
- **Chore tracker** — who's doing what, rotation, kids' allowance. Shared
  calendar underlies this.
- **Medical records** — own + family, ledger-backed. Cross-reference with
  Hesperian for the "is this normal?" question.

## Teaching & skills

- **Skill coach mode** — "teach me to splice rope" → the LLM steps you
  through from the compendium, remembers where you left off. Session state in a
  ledger.
- **Homeschool portfolio** — curriculum delivery (Khan / Wikibooks) +
  progress tracking + printable reports.

## Monitoring

- **Energy dashboard** — solar input, battery state, loads over time. Most
  MPPT controllers speak RS485 or MQTT.
- **Water usage** — well level, cistern, rainfall.
- **Security** — door/window sensors (Zigbee or Z-Wave), IP cams, motion →
  mesh alerts.

## Mapping & local knowledge

- **Annotated OSM** — overlay personal places on the OSM basemap: forage
  spots, friends, broken bridges, water sources, hunting spots.
- **Printable topo book generator** — for a chosen region, generate a
  print-ready PDF of USGS quads + annotations. A paper backup for the oracle.

## Audio / radio

- **Shortwave capture** — scheduled RTL-SDR cron + Whisper transcription into
  RAG. "What did BBC World Service say about X yesterday?"
- **Podcast archive** — download + ingest transcripts.

## Open market (eBay-for-food)

- **Classifieds first** (via Nostr) — "I have / I need" posts with geo.
- **Reputation** — social layer, not technical. Follow/block, "this seller is
  vouched for by X".
- **Settlement** — out of scope. In-person, cash, barter, or whatever the
  parties agree. Avoid the escrow rabbit hole.
- **Barter / time-bank ledger** — track exchanges with neighbors; useful
  without a marketplace too.

## Other ideas worth revisiting

- **Workout tracking** — ledger
- **Finance (offline)** — ledger + reports
- **Emergency contact list / decision tree** — the "if I can't reach anyone,
  here's what to do" tree
- **Local currency / mutual credit** — more serious than barter-ledger
- **Livestock management** — ledger
- **Garden planner + log** — overlaps seed library + journal
- **Backup coordinator** — what's backed up where, when last verified

## Out of scope (for now)

- Anything that requires near-100% internet uptime
- Social features that fundamentally need public-internet-scale discovery
- DRM-encumbered content (Netflix-style)
- Realtime voice/video over mesh (physics won't cooperate)

---

## Suggested build order

The sequence that unlocks the most features per unit effort:

1. Model selection + Ledger primitive (foundations, both shipping now)
2. Food inventory on top of the ledger (first daily-use app)
3. Services skeleton + Calibre-Web + Radicale
4. Nostr relay on each pergamon
5. Classifieds board over Nostr
6. Weather bridge (needs hardware purchase)
7. Everything else, one feature at a time, each leaning on 1–5

---

## Adjacent projects worth cribbing from

We're not duplicating anything well-known — nobody else combines offline LLM +
browseable wiki corpus + RAG across both + config-driven installer + mesh
story. But each slice has prior art worth studying.

### Direct cousins (offline knowledge appliances — no LLM layer)

- **Kiwix Hotspot** — Pi-based turnkey knowledge appliance from the Kiwix
  team. Study their hardware-install UX.
- **Internet-in-a-Box (IIAB)** — long-running project for low-connectivity
  schools. Bundles Kiwix, Khan Academy, OpenStreetMap, KA Lite, RACHEL
  content. *Steal their content curation taxonomy for `corpus/compendium.yaml`.*
- **RACHEL** (World Possible) — same niche as IIAB.
- **LibraryBox / PirateBox** (archived) — ancestors; LAN-only file sharing.
  The "zero-config appliance" design philosophy still holds up.

### Offline LLM / local RAG tools

- **Open WebUI** — the closest public thing to our web UI; mature document
  upload + RAG. *Compare our `rag/web.py` to theirs before polishing much
  further.*
- **PrivateGPT / h2oGPT / LocalGPT** — developer-oriented RAG stacks; good
  reference for chunking strategies, reranking.
- **GPT4All / LM Studio** — desktop chat apps with model pickers. Study
  their model catalog UX.
- **AnythingLLM** — Docker-first local RAG. Workspace concept is nice.

### Preparedness content archives

- **Survivor Library** — massive PDF collection (public domain). *Mine for
  survival compendium entries — much of it is already in our target scope.*
- **Prepper's Library** repos on GitHub — curated PDF collections, static.

### Mesh / distributed protocol prior art

- **Reticulum (RNS)** — the serious engineering alternative to Meshtastic;
  supports LoRa, packet radio, TCP. *Study their abstractions when evolving
  our comms module beyond the Meshtastic skeleton.*
- **Nostr** — relay-based distributed messaging. *This is the one we should
  actually build on; see Foundations section.*
- **Secure Scuttlebutt (SSB)** — older social protocol with friend-graph
  model. Slower community but strong design.
- **Briar** — offline-first messaging over Bluetooth/Tor/Wi-Fi. *Study the
  mesh-DM model for Meshtastic reply patterns.*
- **Yggdrasil / cjdns** — mesh networking overlays. Overkill for us but good
  reference.

### In-home services (services/ territory)

- **CasaOS / Umbrel / YunoHost / Start9 embassyOS** — "home server" distros,
  each with one-click installs for 50+ self-hosted apps. *Steal the service
  catalog pattern.* Our `services/` module should feel this polished.
- **TrueNAS SCALE** — NAS + k8s apps. Heavier than we need.

### Concrete action items from this

Adding to backlog, by project they're inspired by:

- **From Open WebUI**: file-drop into web UI → queue chunking into Chroma;
  chat history persistence; multi-turn conversations.
- **From IIAB**: the shelf taxonomy (we already crib loosely); add
  `age_group:` and `language:` fields to catalog entries for school-use.
- **From Umbrel / CasaOS**: services module should have a one-screen
  "available apps" catalog with install/uninstall toggles — mirror the
  corpus catalog pattern.
- **From Reticulum**: add a Reticulum transport backend to the comms module
  alongside Meshtastic — for packet radio over HF (slower but much longer
  range).
- **From Briar**: for Meshtastic DMs, store-and-forward when the recipient
  isn't currently reachable. Queue; retry on next heartbeat.
- **From Nostr**: ship a relay container as part of services/. First
  dependent app is distributed classifieds.
- **From Survivor Library**: scripted importer that walks a mirror of their
  PDF collection, filters by category, dedupes against our existing corpus.
- **From Open WebUI**: look at their embeddings UI before we commit heavily
  to our current model-picker design — they may have figured out the
  "reindex now" prompt better than us.
- **From GPT4All / LM Studio**: our model catalog could auto-benchmark
  tokens/sec per model on first run so the setup TUI can recommend one
  that'll feel fast.

### Positioning statement

Pergamon's unique combination: offline LLM + browseable corpus + RAG across
both + config-driven installer + mesh story. If someone else ships
something that covers all five, we revisit. Until then: borrow freely,
reinvent nothing we don't have to.

---

## Capturing new ideas

Add them to the appropriate section above, with a one-line pitch. When an idea
graduates to "I actually want this," open a GitHub issue referring back here
and move it to the roadmap.
