# Comms — Meshtastic bridge

Let a Meshtastic node send a DM to this pergamon and get a RAG-synthesized answer back over LoRa.

## Usage

```bash
pergamon mesh mock              # dev mode: stdin → chunked answer, no radio
pergamon mesh listen            # production mode: USB-attached node
MESHTASTIC_PORT=/dev/tty.usbserial-0001 pergamon mesh listen
```

The reply is auto-chunked to fit Meshtastic's ~240-byte payload with `[p/N]` prefixes so recipients can reassemble.

## Hardware

Any Meshtastic-supported board works. Three common choices:

| Board | Notes |
|---|---|
| **Heltec V3 (LoRa 32)** | ~$25, great starter, built-in OLED, USB-C |
| **RAK WisBlock 4631** | Modular, better battery options, pricier |
| **LILYGO T-Beam** | GPS on board, bigger battery, good for mobile use |

Flash the latest Meshtastic firmware via https://flasher.meshtastic.org (web-based, no toolchain).

## Pairing

1. Plug the node into the pergamon machine via USB.
2. Confirm it's visible: `ls /dev/tty.usbserial*` (macOS) or `ls /dev/ttyUSB*` (Linux).
3. Start the listener: `pergamon mesh listen`.
4. From another Meshtastic client (Android/iOS app, or another node), send a **DM** (not broadcast) to the pergamon's node. Broadcast traffic is deliberately ignored to avoid flooding.

## Allowlist (optional)

By default, the pergamon answers DMs from any node. To restrict:

```yaml
# config/install.local.yaml
comms:
  meshtastic:
    allowed_node_ids:
      - "!abcd1234"      # your own handheld
      - "!deadbeef"      # another family member's node
```

Node IDs appear as `!hexstring` and are stable per device. You'll see them in Meshtastic client UIs or in `pergamon mesh listen`'s logs.

## Why DMs only

A broadcast on channel 0 reaches every node in range. Replying to broadcasts means a single open question could spam a whole regional mesh with 5–10 LoRa packets of answer. DMs keep the traffic point-to-point.

## Current state: skeleton

Mock mode is fully exercised: `pergamon mesh mock` runs the RAG and renders the chunked reply.

The real-radio path (`pergamon mesh listen`) is written but **unverified in this build** — no Meshtastic hardware was attached when the module was authored. The first operator with a device should:

1. Run `pergamon mesh listen` and confirm the device opens.
2. DM the node from another Meshtastic client.
3. Watch the terminal — you should see the inbound message logged and the outbound chunks going out.

Report any issues in the project tracker.
