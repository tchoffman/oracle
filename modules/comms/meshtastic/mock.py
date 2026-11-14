"""Mock mesh mode: reads questions from stdin, prints chunked answers.

Lets you develop + test the pergamon's mesh persona without a radio.
Same ask → chunking → reply path as the real listener.
"""
from __future__ import annotations

import sys
from time import sleep

from rich.console import Console

from modules.comms.meshtastic.common import MAX_MESH_CHARS, ask

console = Console()


def main() -> int:
    console.print("[bold cyan]pergamon mesh (mock)[/bold cyan] — type a question, blank line to quit")
    while True:
        try:
            q = input("mesh> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not q:
            return 0

        reply = ask(q)
        chunks = reply.chunks()
        console.print(f"[dim]→ {len(chunks)} LoRa packet(s), ~{MAX_MESH_CHARS} chars each[/dim]")
        for c in chunks:
            console.print(f"[green]{c}[/green]")
            sleep(0.2)  # simulate inter-packet delay
        console.print()


if __name__ == "__main__":
    sys.exit(main())
