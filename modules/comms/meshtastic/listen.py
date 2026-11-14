"""Listen for Meshtastic DMs and reply with a RAG-chunked answer.

Real-hardware path. Needs a Meshtastic device attached via USB (the serial
interface) or reachable over TCP.

Safety:
- Only answers DMs (private channel). Broadcast traffic is ignored.
- Optionally restrict to an allowlist of node IDs (see config/install.local.yaml
  under comms.meshtastic.allowed_node_ids).
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from rich.console import Console

from modules.comms.meshtastic.common import ask
from rag.install_config import load_yaml, INSTALL_LOCAL_PATH

console = Console()


def _load_allowed_nodes() -> set[str]:
    cfg = load_yaml(INSTALL_LOCAL_PATH) if INSTALL_LOCAL_PATH.exists() else {}
    allowed = (((cfg.get("comms") or {}).get("meshtastic") or {}).get("allowed_node_ids")) or []
    return {str(x) for x in allowed}


def _reply(iface: Any, dest_id: str, reply):
    chunks = reply.chunks()
    console.print(f"[dim]  → {len(chunks)} LoRa packet(s)[/dim]")
    for c in chunks:
        iface.sendText(c, destinationId=dest_id)
        time.sleep(1.2)  # be gentle on the airwaves


def on_receive(packet: dict, interface) -> None:
    """Called by Meshtastic's pubsub for each received packet."""
    decoded = packet.get("decoded") or {}
    if decoded.get("portnum") != "TEXT_MESSAGE_APP":
        return
    text = decoded.get("text") or ""
    sender = packet.get("fromId") or str(packet.get("from"))
    channel = packet.get("channel", 0)

    # Only DMs — channel 0 broadcast would spam the whole mesh.
    to_id = packet.get("toId") or str(packet.get("to"))
    is_dm = to_id and to_id != "^all"
    if not is_dm:
        return

    allowed = _load_allowed_nodes()
    if allowed and sender not in allowed:
        console.print(f"[yellow]ignoring DM from unallowed node {sender}[/yellow]")
        return

    console.print(f"[bold]{sender}[/bold] (ch {channel}): {text}")
    try:
        reply = ask(text)
        _reply(interface, sender, reply)
    except Exception as e:
        console.print(f"[red]ask failed: {e}[/red]")
        interface.sendText(f"[pergamon] error: {e}"[:200], destinationId=sender)


def main() -> int:
    try:
        import meshtastic.serial_interface as serial_iface
    except ImportError:
        console.print("[red]meshtastic package not installed[/red]")
        return 1
    try:
        from pubsub import pub
    except ImportError:
        console.print("[red]pypubsub not installed (comes with meshtastic)[/red]")
        return 1

    port = os.environ.get("MESHTASTIC_PORT")  # /dev/tty.usbserial-* on mac
    console.print(f"[cyan]opening Meshtastic serial interface[/cyan] (port={port or 'auto'})")
    try:
        iface = serial_iface.SerialInterface(devPath=port) if port else serial_iface.SerialInterface()
    except Exception as e:
        console.print(f"[red]no device found: {e}[/red]")
        console.print("Try:  pergamon mesh mock      # develop without a radio")
        return 1

    allowed = _load_allowed_nodes()
    if allowed:
        console.print(f"[dim]allowed node IDs: {sorted(allowed)}[/dim]")
    else:
        console.print("[yellow]no allowlist set — responding to all DMs[/yellow]")

    pub.subscribe(on_receive, "meshtastic.receive")

    console.print("[green]ready. ctrl-c to quit.[/green]")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[dim]closing[/dim]")
        iface.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
