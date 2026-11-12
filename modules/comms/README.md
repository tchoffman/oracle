# Module 1 — Comms (radio, mesh, cross-pergamon sync)

**Status:** planning. See [../../docs/roadmap.md](../../docs/roadmap.md) for context.

## Scope

Three kinds of no-internet comms the pergamon should learn to speak:

1. **Receive-only shortwave** — news/weather/time signals. No license.
2. **Ham radio** — HF digital, VHF/UHF simplex. Licensed TX.
3. **LoRa mesh** — Meshtastic / Reticulum / Meshcore. License-free in ISM bands.

## Planned layout

```
modules/comms/
├── shortwave/      # SDR + whisper transcription of recorded broadcasts
├── meshtastic/     # Meshtastic Python client, pubsub bridge
├── reticulum/      # RNS-based transport; more robust than Meshtastic
├── aprs/           # Direwolf + Baofeng cable; beacons + short messages
└── sync/           # Cross-pergamon delta protocol (signed, chunked)
```

## Not-yet-decided

- Which mesh protocol wins? Meshtastic is the biggest community; Reticulum is the better engineering. Probably support both.
- Delta format for cross-pergamon sync — reuse an existing format (Nostr relay deltas? Patch over git bundles?) vs. roll our own.
- Trust model — PGP-style web of trust between pergamon operators.

## First milestone

A tiny proof of concept: pergamon receives a query over Meshtastic DMs, replies with a <~2KB summary over multiple LoRa packets. No fancy sync yet. Just prove the LLM can be reached when the internet is down.
