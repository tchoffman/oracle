# Nostr relay

A single-node [Nostr](https://github.com/nostr-protocol/nips) relay running on
your pergamon. This is the backbone for all cross-machine features that
cross the internet or a mesh — social posts, direct messages, the planned
classifieds marketplace, weather sharing, news digests.

## What is Nostr, briefly

- Clients publish signed events (text notes, DMs, long-form posts, …) to
  relays.
- Relays store and forward events; clients subscribe by filter.
- No central server — if one relay dies, your events are still on the
  others you're connected to. If the internet dies, mesh-connected
  pergamons can still exchange events over LoRa (future work).

Each pergamon runs a relay (this one) and clients the owner trusts.

## Starting

```bash
pergamon services up nostr-relay
```

Relay URL: `ws://<pergamon-ip>:8091/`

Test it:

```bash
# From any Nostr client — e.g. nak (https://github.com/fiatjaf/nak):
nak req -k 1 --limit 10 ws://localhost:8091
```

## Using it

Point any Nostr client at `ws://<pergamon-ip>:8091`:

- **Damus** / **Amethyst** / **nos2x** / **Alby** — mobile + browser clients
- **nak** — command-line
- **noscl**, **nostril** — scripting

Publish a note; subscribe to friends' pubkeys who also run pergamons.

## Peering with other pergamons

Nothing automatic yet. Manually:

1. Ask your peer for their relay URL: `ws://their-pergamon-ip:8091`
2. Add it to your client's relay list.
3. They do the same for yours.

Future work (see `docs/ideas.md`): a mesh directory that auto-propagates
peer relay URLs as nodes come up on the Meshtastic network.

## Authorization

By default the relay is **open** — anyone who can reach port 8091 can
publish. For LAN use that's usually fine. To lock it down, edit
`config.toml`:

```toml
[authorization]
pubkey_whitelist = ["npub1yourpubkeyhere", "npub1familymember..."]
```

Then: `pergamon services restart nostr-relay`.

## Storage

SQLite DB in `../../build/services/nostr-relay/data/`. Grows with retained
events. Back up periodically.

## What this unlocks

The classifieds marketplace, the distributed social feed, DMs that work
over internet-or-mesh — none of these need new protocols. Each is a schema
on top of events. See `docs/ideas.md` → "Cross-machine apps" for the
backlog.
