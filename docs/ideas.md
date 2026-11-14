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

## Non-Pergamon on-ramps

Most community members won't run their own Pergamon. The network has to
have low-tech entry points or it's a toy for a technical minority.

Ranked by cost-to-adopt (lowest first):

- **★ Physical bulletin board at each host site.** Printed from Nostr feed
  daily/weekly; paper slips pinned under headings; old ones culled.
  Zero-tech read access for anyone who walks in.
- **★ Paper forms with QR routing.** Standardized printable forms
  (classified / help-wanted / lost-found / event / DM / trade-receipt).
  QR header encodes `form_type/version/host_site_id`. Users drop them in
  a literal mailbox at the host site; admin scans in batches; OCR +
  manual review posts them to Nostr.
- **Member card (QR npub).** Each member gets a printed card with their
  Nostr public key as a QR. Host scans card + form together; posts are
  signed on the user's behalf via a delegation key. Audit trail shows
  "Alice via Host-Pergamon-NC" so trust is attributable.
- **SMS bridge.** Host runs a cellular modem or shares a phone with a
  dedicated number. SMS → Nostr post. Replies auto-delivered. Serves
  flip-phone users and people with cell but no smartphone.
- **Walk-in terminal.** The pergamon machine itself has keyboard + display
  in a library-style corner at the host. Signed posting via member-card
  scan. For people who want to type but don't own a device.
- **Shortwave / ham bridge.** Scheduled HF receive at the host; hand- or
  Whisper-transcribed notices → Nostr. Return direction via WSPR / FT8
  for very-low-bandwidth broadcast.
- **Guest PWA.** NFC tag at the host opens the web UI on any passing
  phone; session-signs with a temporary key that expires. For travelers.

### Making paper forms actually work

The failure mode is admin burnout. Design accordingly:

- Standardized OCR-friendly layouts — tick boxes, pre-printed fields,
  high contrast. Think IRS forms, not freeform.
- QR header routes automatically to the right Nostr kind.
- One item per form — no multi-item slips.
- Member-card QR slot at the top for signed posting on the user's behalf.
- Pre-dated **trade receipts** that both parties sign create the audit
  trail everything else piggybacks on.
- Host maintains a physical scanned-forms folder; participants can audit
  whether their post made it through.
- The host is a notary: trusted to scan accurately, trusted not to
  fabricate, trusted not to redistribute DMs. The host's reputation is
  on the line.

### Standard form library (starter set)

Printable PDFs the host keeps in a tray:

1. Classified: buy / sell / trade / want
2. Help wanted (labor exchange, work parties)
3. Lost & found
4. Event notice (potluck, swap meet, work bee, service)
5. Direct message to another member
6. Trade receipt (both signatures)
7. Local news / notice
8. New-member application (name + contact + member-card QR)

## Monetary base: junk silver

Barter is awkward without a common denominator. Use pre-1965 US 90% Ag
coinage ("junk silver") as the reference. Rationale:

- Widely held by the target community already
- Universal recognition
- Fine divisibility (dime ≈ 0.0715 oz Ag)
- Trusted provenance (US Mint)
- Historical precedent as inflation hedge
- Testable with ring / specific-gravity / magnet / date checks

### Standardize on

- **Unit of account: troy ounces of silver (`oz_ag`).** Matches commodity
  spot markets; easy conversion.
- **Display: silver dimes alongside `oz_ag`.** 1 dime ≈ 0.0715 oz Ag.
  Small trades read naturally either way.
- **Secondary units for context:**
  - USD-equivalent via a cached spot price (any Pergamon with internet
    broadcasts; offline peers cache the last seen rate)
  - Labor-hours — "a day's work" as an alternate barter standard
  - kWh — useful for energy-dense goods in off-grid contexts

### Schema touchpoints

Classified ad fields:

- `price_oz_ag` (optional)
- `price_usd` (optional, cached rate)
- `accepts`: array of {`silver`, `cash`, `barter`, `labor`, `kwh`}
- `will_accept_offers` (bool)

User profile:

- `preferred_tender` — "silver + barter" / "USD only" / etc. Browsing
  respects this.

Trade receipt:

- Both sides record what was actually exchanged. Useful for dispute
  resolution and for historical rate reconstruction.

Spot-price updater:

- Scheduled job on any Pergamon with internet
- Publishes a canonical event (e.g. `kind: 30301`) with the day's spot
- Peers cache locally

### Testing authenticity (worth including in `docs/`)

- **Ring test** — 90% Ag coins ring higher/brighter than clad
- **Specific gravity** — 90% Ag = 10.34 g/cm³
- **Magnet** — silver is non-magnetic; some counterfeits aren't
- **Date check** — pre-1965 US dimes/quarters; pre-1964 halves (post-1964
  halves are 40% Ag through 1970); Mercury dimes always 90%; Roosevelt
  1946–1964 90%
- **Weight** — a dime is 2.5 g, quarter 6.25 g, half 12.5 g

Add a one-pager `docs/silver-reference.md` with these + conversion
tables + typical spot-to-dime conversions at various price points.

## Identity & community reputation

### ★ Identity (foundational — build before/with classifieds)

Each user has a Nostr keypair. Private key (`nsec`) is the secret account ID
they use to sign into any pergamon distributed app. Public key (`npub`) is
their cross-pergamon identifier.

Reputation = a bundle of signals, computed per-viewer (no global score):

- Who follows them (NIP-02)
- NIP-05 verified name via a pergamon domain (`trenton@mypergamon.local`)
- Age of key + activity history on the local relay
- Positive endorsements (NIP-25 reactions / list memberships)
- Peer-circle depth: "4 of your 10 closest peers follow them"

Login flow: client holds the nsec and signs events. No passwords. No
server-side auth. Standard Nostr clients already implement this.

Build cost: small. Mostly a `pergamon identity` command for key generate /
export / rotate, plus a NIP-05 verifier endpoint on the local relay.

### Community reports (high-risk; design before building)

**Framing:** "local witness reports," not "most wanted." Lets victims get
on-record and warn neighbors about predatory behavior; a real need in
low-institution contexts. But reputation-weighted accusation systems have a
bad historical track record (false accusations, ethnic targeting, mob
dynamics, weaponized disputes). Build carefully or not at all.

Non-negotiable guardrails if built:

- **Signed reports only.** No anonymous accusations — your reputation is on
  the line too.
- **Local-circle scope.** Reports travel your peers' relays, not globally.
- **Weighted by reporter-rep × N independent reporters.** Drive-by low-rep
  post → near-zero weight.
- **Subject can reply** (reply event attached). Mediation outcomes attach
  too — resolved / unfounded / retracted / confirmed by elder.
- **Default 12-month expiry** unless renewed.
- **Audit log of every report by a given author** — repeat false accusers
  self-weight-down.
- **Explicit opt-in stream.** Doesn't contaminate classifieds / social.
- **Photos only with a consent framework** — subject's npub tagged; they
  can dispute. Minors not allowed at all.
- **LLM doesn't ground answers in reports.** `pergamon ask` returns
  factual references; contested accusations are not facts.

Risks that persist even with all guardrails:

- Weaponized divorces / business-rival accusations
- Out-group targeting (ethnic, religious, political)
- Legal exposure (defamation applies to electronic publication)
- Chilling effect on newcomers — pushes communities toward xenophobia

**Suggested first step:** skip the structured witness-report system and
ship a plain **"local news / local notices" section** on the classifieds
message board. Lower system risk (it's just a thread); the social layer
does the enforcement. This is how real towns have handled this forever
(the bulletin board at the general store). Build the formal system only
after watching the simple version in production.

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
