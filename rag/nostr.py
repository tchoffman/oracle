"""Nostr event builder + relay publisher.

Enough Nostr to sign a kind-N event with the active identity's key and
publish it to configured relays over WebSocket. Pure stdlib + coincurve
+ websockets — no heavyweight client lib.

CLI:
    pergamon nostr post "hello world"              # kind 1 (short note)
    pergamon nostr post --kind 1 -t t,pergamon "..."
    pergamon nostr relays                           # list configured relays
    pergamon nostr relays add ws://...              # register another relay

Default relay: whichever one is configured in config/install.local.yaml
under `nostr.relays:`, else ws://localhost:8091/ (the one that ships with
the nostr-relay service).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import websockets
from coincurve import PrivateKey
from coincurve.keys import PublicKeyXOnly
from rich.console import Console

from rag.config import REPO_ROOT, load_config
from rag.identity import (
    _bech32_to_hex,
    get_active,
    load_identity,
    load_nsec,
)
from rag.install_config import INSTALL_LOCAL_PATH, load_yaml

console = Console()

DEFAULT_RELAY = "ws://localhost:8091/"


# ─────────────────────────── event model ─────────────────────────────

@dataclass
class Event:
    kind: int
    content: str
    pubkey: str                          # hex, 64 chars
    tags: list[list[str]] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))
    id: str = ""
    sig: str = ""

    def serialize_for_id(self) -> str:
        """Canonical serialization per NIP-01."""
        return json.dumps(
            [0, self.pubkey, self.created_at, self.kind, self.tags, self.content],
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": self.tags,
            "content": self.content,
            "sig": self.sig,
        }


def _compute_id(event: Event) -> str:
    return hashlib.sha256(event.serialize_for_id().encode("utf-8")).hexdigest()


def sign_event(event: Event, nsec: str, aux_rand: bytes | None = None) -> Event:
    """Fill in event.id and event.sig in-place. Returns the event for chaining."""
    hex_sec = _bech32_to_hex("nsec", nsec)
    sk = PrivateKey(bytes.fromhex(hex_sec))
    event.id = _compute_id(event)
    msg = bytes.fromhex(event.id)
    aux = aux_rand if aux_rand is not None else os.urandom(32)
    event.sig = sk.sign_schnorr(msg, aux).hex()
    return event


def verify_event(event: Event) -> bool:
    """Check id matches the content and sig is valid against pubkey."""
    if event.id != _compute_id(event):
        return False
    try:
        pk = PublicKeyXOnly(bytes.fromhex(event.pubkey))
        return pk.verify(bytes.fromhex(event.sig), bytes.fromhex(event.id))
    except Exception:
        return False


def build_event(
    kind: int,
    content: str,
    pubkey_hex: str,
    tags: list[list[str]] | None = None,
) -> Event:
    return Event(kind=kind, content=content, pubkey=pubkey_hex, tags=tags or [])


# ───────────────────────── relay WebSocket ───────────────────────────

async def _publish_one(relay_url: str, event: Event, timeout: float = 10.0) -> tuple[bool, str]:
    """Send a single event to one relay. Returns (ok, message)."""
    try:
        async with websockets.connect(relay_url, open_timeout=timeout) as ws:
            await ws.send(json.dumps(["EVENT", event.to_json()]))
            # Relays typically reply with ["OK", event_id, true/false, "message"].
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    return False, "timeout waiting for OK"
                msg = json.loads(raw)
                if not isinstance(msg, list) or not msg:
                    continue
                if msg[0] == "OK" and len(msg) >= 3 and msg[1] == event.id:
                    accepted = bool(msg[2])
                    reason = msg[3] if len(msg) > 3 else ""
                    return accepted, reason
                if msg[0] == "NOTICE" and len(msg) >= 2:
                    # Non-fatal; keep waiting for OK.
                    continue
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def _publish_many(event: Event, relay_urls: list[str]) -> dict[str, tuple[bool, str]]:
    results = await asyncio.gather(*(_publish_one(u, event) for u in relay_urls))
    return {u: r for u, r in zip(relay_urls, results)}


def publish(event: Event, relay_urls: list[str]) -> dict[str, tuple[bool, str]]:
    """Blocking publish. Returns per-relay (ok, message)."""
    return asyncio.run(_publish_many(event, relay_urls))


# ─────────────────────── relay config helpers ────────────────────────

def _load_relays_from_config() -> list[str]:
    local = load_yaml(INSTALL_LOCAL_PATH) if INSTALL_LOCAL_PATH.exists() else {}
    relays = ((local.get("nostr") or {}).get("relays")) or []
    if not relays:
        return [DEFAULT_RELAY]
    return list(relays)


def _save_relays(relays: list[str]) -> None:
    local = load_yaml(INSTALL_LOCAL_PATH) if INSTALL_LOCAL_PATH.exists() else {}
    local.setdefault("nostr", {})["relays"] = relays
    import yaml
    with open(INSTALL_LOCAL_PATH, "w") as f:
        yaml.safe_dump(local, f, sort_keys=False, default_flow_style=False)


# ────────────────────────────── CLI ──────────────────────────────────

def _cmd_post(argv: list[str]) -> int:
    kind = 1
    tags: list[list[str]] = []
    content_parts: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--kind" and i + 1 < len(argv):
            kind = int(argv[i + 1]); i += 2
        elif a in ("-t", "--tag") and i + 1 < len(argv):
            parts = argv[i + 1].split(",", 1)
            tags.append([parts[0]] + ([parts[1]] if len(parts) > 1 else []))
            i += 2
        else:
            content_parts.append(a); i += 1
    content = " ".join(content_parts).strip()
    if not content:
        console.print("Usage: pergamon nostr post [--kind N] [-t name,value] \"content\"")
        return 2

    ident = get_active()
    if not ident:
        console.print("[red]no active identity.[/red] Create one with: pergamon identity create <name>")
        return 1
    nsec = load_nsec(ident.name)

    event = sign_event(
        build_event(kind=kind, content=content, pubkey_hex=ident.hex_pub, tags=tags),
        nsec,
    )
    relays = _load_relays_from_config()
    console.print(f"[dim]publishing to {len(relays)} relay(s)[/dim]")
    results = publish(event, relays)
    any_ok = False
    for url, (ok, msg) in results.items():
        mark = "[green]ok[/green]" if ok else "[red]fail[/red]"
        console.print(f"  [{mark}] {url}  {msg}")
        any_ok = any_ok or ok

    console.print(f"\nevent id: [cyan]{event.id}[/cyan]")
    console.print(f"kind: {event.kind}  from: {ident.npub}")
    return 0 if any_ok else 1


def _cmd_relays(argv: list[str]) -> int:
    if not argv or argv[0] == "list":
        for r in _load_relays_from_config():
            print(r)
        return 0
    if argv[0] == "add" and len(argv) >= 2:
        current = _load_relays_from_config()
        new = argv[1]
        if new not in current:
            current.append(new)
            _save_relays(current)
            console.print(f"[green]added[/green] {new}")
        else:
            console.print(f"[yellow]already configured:[/yellow] {new}")
        return 0
    if argv[0] == "rm" and len(argv) >= 2:
        current = _load_relays_from_config()
        new = [r for r in current if r != argv[1]]
        if len(new) == len(current):
            console.print(f"[yellow]not in list:[/yellow] {argv[1]}")
            return 1
        _save_relays(new)
        console.print(f"[green]removed[/green] {argv[1]}")
        return 0
    console.print("Usage: pergamon nostr relays {list|add URL|rm URL}")
    return 2


def main(argv: list[str]) -> int:
    if not argv:
        console.print(
            "Usage:\n"
            "  pergamon nostr post [--kind N] [-t name,value] \"content\"\n"
            "  pergamon nostr relays [list|add URL|rm URL]"
        )
        return 2
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "post":
        return _cmd_post(rest)
    if cmd == "relays":
        return _cmd_relays(rest)
    console.print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
