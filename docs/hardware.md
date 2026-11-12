# Hardware & deployment notes

This doc covers two machines: **the dev box** (what we're building on) and **the cage machine** (the long-term off-grid appliance).

## Dev box

Target: Apple Silicon Mac, 16GB RAM, ~100GB free disk.

- 8B-class model runs at usable speed (>10 tok/s on M4) with Metal acceleration via Ollama.
- Starter corpus (~10GB of ZIMs + PDFs) comfortably fits alongside the model.
- Full English Wikipedia (57GB nopic / 100GB+ with images) will not fit; starter corpus uses Simple English Wikipedia instead.

## Cage machine (long-term)

**Goal:** a sealed, EMP-hardened unit you can pull out when things go very wrong, plus a running copy for everyday use.

### Minimum viable cage machine

| Component | Pick | Why |
|-----------|------|-----|
| Compute   | Mac Mini M4, 32GB RAM, 1–2TB SSD | ~10W idle, ~40W inference. Runs 32B-class models at reasonable speed; full Wikipedia-with-images fits easily. |
| Storage   | 2× external SSD, mirrored (ZFS / software RAID / just rsync) | One SSD dies, pergamon lives. |
| Power     | 400W solar panel + 1–2 kWh LiFePO4 + MPPT charge controller + pure-sine inverter | Can run the Mac Mini for hours daily, charge devices on the side. |
| Display   | Small efficient monitor OR plug into a laptop over sidecar/USB-C | Only needed when actually using it. |
| Comms     | Baofeng UV-5R (ham, needs Technician license) + Tecsun PL-330 (shortwave rx) | Information in; limited coordination out. |

### Faraday considerations

EMP is one of several off-grid scenarios and not the most probable. Treat the cage as **insurance**, not primary storage.

- **Daily driver** lives outside the cage. All day-to-day use is on the live machine so the index stays fresh and failures surface before they matter.
- **Cold spare** in the cage: a **cloned** SSD + a spare mini with no connections. Build this once the primary works.
- Protect **everything downstream of the solar panel** that you'd need to charge the spare: at minimum the charge controller, inverter, and a USB charger. Panels themselves are reasonably EMP-robust.
- Simple sealed metal trash can with gasket tape works. Grounding matters less than sealing.

### Power budget sanity check

- Mac Mini M4 idle: ~5W; typical use: ~30W; inference peak: ~45W
- Running 3h/day at ~30W → ~90Wh/day. A 1kWh battery is >10 days of autonomy.
- Solar: 400W panel on a decent day → ~2kWh. Easy recharge.

### What NOT to include in the cage

- Anything with its own radio you'd want running (phones, LTE hotspots, routers) — they're useless indoors with no external antenna anyway.
- Lithium batteries while hot/charging — put a spare pack in instead.
- Fuel or backup generators (fire risk; separate storage).

## Threat scenarios ranked by probability (loose)

1. **Multi-day grid outage** — hurricane, ice storm, wildfire. Daily driver + solar handles this.
2. **Supply chain disruption** — extended shortages but power + comms are fine. Pergamon useful for recipes, repairs, triage.
3. **Extended off-grid lifestyle** — cabin, van, boat. Same as #2 but constant.
4. **EMP / cyberattack on grid** — probable scope: regional, weeks. Cage spare comes out.
5. **Societal collapse** — low probability; everything else is still useful.
