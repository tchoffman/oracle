"""Classifieds — NIP-99 addressable "classified listing" events (kind 30402).

Standard tags per NIP-99:
    ["d", unique-id]            (required for addressable kinds)
    ["title", text]
    ["summary", text]
    ["price", amount, currency]
    ["location", text]
    ["t", hashtag]              (repeated)
    ["published_at", unix_ts]
    ["status", "active" | "sold"]
    ["image", url]              (repeated; optional)

Pergamon extensions (used alongside the standard tags, not in place of them):
    ["price", amount, "oz_ag"]   — our junk-silver unit of account
    ["accepts", "silver,barter,labor,cash,kwh"]
    ["pergamon:hosted-by", host_npub]   — when posted via a host on behalf

CLI:
    pergamon classified post --title "20lb apples" --price-oz-ag 0.3 \\
        --accepts silver,barter -t apples -t harvest "Honeycrisp, pick-up only"

    pergamon classified list                                  # top 50 recent
    pergamon classified list --tag apples
    pergamon classified search "chicken"                      # client-side filter
"""
from __future__ import annotations

import asyncio
import json
import secrets
import sys
import time
from dataclasses import dataclass
from typing import Any

import websockets
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rag.identity import get_active, load_nsec
from rag.nostr import (
    Event,
    _load_relays_from_config,
    build_event,
    publish,
    sign_event,
    verify_event,
)

console = Console()

KIND_CLASSIFIED = 30402
DEFAULT_LIMIT = 50


# ────────────────────────── build + post ────────────────────────────

def build_listing_event(
    pubkey_hex: str,
    title: str,
    description: str,
    *,
    price_oz_ag: float | None = None,
    price_usd: float | None = None,
    accepts: list[str] | None = None,
    location: str | None = None,
    summary: str | None = None,
    hashtags: list[str] | None = None,
    status: str = "active",
    listing_id: str | None = None,
    image_urls: list[str] | None = None,
) -> Event:
    """Build an unsigned kind-30402 event. Caller signs + publishes."""
    tags: list[list[str]] = []
    listing_id = listing_id or secrets.token_hex(8)
    tags.append(["d", listing_id])
    tags.append(["title", title])
    if summary:
        tags.append(["summary", summary])
    if price_oz_ag is not None:
        tags.append(["price", str(price_oz_ag), "oz_ag"])
    if price_usd is not None:
        tags.append(["price", str(price_usd), "USD"])
    if accepts:
        tags.append(["accepts", ",".join(accepts)])
    if location:
        tags.append(["location", location])
    tags.append(["published_at", str(int(time.time()))])
    tags.append(["status", status])
    for h in hashtags or []:
        tags.append(["t", h])
    for u in image_urls or []:
        tags.append(["image", u])

    return build_event(kind=KIND_CLASSIFIED, content=description, pubkey_hex=pubkey_hex, tags=tags)


def summarize(event: Event) -> dict:
    """Pull the useful fields out of a classified event for display / filtering."""
    tags = {t[0]: t[1:] for t in event.tags}  # last-wins on dupe keys; fine for our fields
    out = {
        "id": event.id,
        "pubkey": event.pubkey,
        "created_at": event.created_at,
        "d": tags.get("d", [""])[0],
        "title": tags.get("title", [""])[0],
        "summary": tags.get("summary", [""])[0],
        "location": tags.get("location", [""])[0],
        "status": tags.get("status", ["active"])[0],
        "description": event.content,
        "hashtags": [t[1] for t in event.tags if t[0] == "t" and len(t) >= 2],
        "accepts": [],
        "price_oz_ag": None,
        "price_usd": None,
    }
    for t in event.tags:
        if t[0] == "price" and len(t) >= 3:
            try:
                amount = float(t[1])
            except ValueError:
                continue
            if t[2] == "oz_ag":
                out["price_oz_ag"] = amount
            elif t[2] == "USD":
                out["price_usd"] = amount
        elif t[0] == "accepts" and len(t) >= 2:
            out["accepts"] = [x.strip() for x in t[1].split(",") if x.strip()]
    return out


# ───────────────────────── fetch from relays ───────────────────────

async def _subscribe_and_collect(
    relay_url: str,
    filters: dict,
    max_events: int,
    timeout: float = 10.0,
) -> list[Event]:
    """Open a REQ subscription on one relay, collect events until EOSE or max_events."""
    events: list[Event] = []
    sub_id = secrets.token_hex(4)
    try:
        async with websockets.connect(relay_url, open_timeout=timeout) as ws:
            await ws.send(json.dumps(["REQ", sub_id, filters]))
            while len(events) < max_events:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                if not isinstance(msg, list) or not msg:
                    continue
                if msg[0] == "EVENT" and len(msg) >= 3 and msg[1] == sub_id:
                    raw_event = msg[2]
                    ev = Event(
                        kind=raw_event["kind"],
                        content=raw_event["content"],
                        pubkey=raw_event["pubkey"],
                        tags=raw_event.get("tags", []),
                        created_at=raw_event["created_at"],
                        id=raw_event["id"],
                        sig=raw_event["sig"],
                    )
                    if verify_event(ev):
                        events.append(ev)
                elif msg[0] == "EOSE" and len(msg) >= 2 and msg[1] == sub_id:
                    break
            await ws.send(json.dumps(["CLOSE", sub_id]))
    except Exception as e:
        console.print(f"[yellow]relay {relay_url} error:[/yellow] {e}")
    return events


def fetch_listings(
    relay_urls: list[str],
    tag: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Event]:
    """Pull classified events from relays; de-dupe by id."""
    filters: dict = {"kinds": [KIND_CLASSIFIED], "limit": limit}
    if tag:
        filters["#t"] = [tag]
    all_events: dict[str, Event] = {}
    for url in relay_urls:
        got = asyncio.run(_subscribe_and_collect(url, filters, limit))
        for ev in got:
            all_events[ev.id] = ev
    return sorted(all_events.values(), key=lambda e: e.created_at, reverse=True)


# ────────────────────────────── CLI ────────────────────────────────

def _print_listing(info: dict) -> None:
    price_parts = []
    if info.get("price_oz_ag") is not None:
        price_parts.append(f"{info['price_oz_ag']} oz Ag")
    if info.get("price_usd") is not None:
        price_parts.append(f"${info['price_usd']}")
    if not price_parts:
        price_parts.append("barter")
    head = f"[bold]{info['title'] or '(no title)'}[/bold]  —  {' · '.join(price_parts)}"
    body_lines = []
    if info.get("location"):
        body_lines.append(f"[dim]location:[/dim] {info['location']}")
    if info.get("accepts"):
        body_lines.append(f"[dim]accepts:[/dim] {', '.join(info['accepts'])}")
    if info.get("hashtags"):
        body_lines.append(f"[dim]tags:[/dim] {', '.join('#' + t for t in info['hashtags'])}")
    body_lines.append(f"[dim]status:[/dim] {info['status']}  [dim]from:[/dim] {info['pubkey'][:16]}…")
    body_lines.append("")
    body_lines.append(info["description"])
    console.print(Panel("\n".join(body_lines), title=head, border_style="cyan"))


def _cmd_post(argv: list[str]) -> int:
    title = None
    description_parts: list[str] = []
    price_oz_ag = None
    price_usd = None
    accepts: list[str] = []
    location = None
    hashtags: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--title" and i + 1 < len(argv):
            title = argv[i + 1]; i += 2
        elif a == "--price-oz-ag" and i + 1 < len(argv):
            price_oz_ag = float(argv[i + 1]); i += 2
        elif a == "--price-usd" and i + 1 < len(argv):
            price_usd = float(argv[i + 1]); i += 2
        elif a == "--accepts" and i + 1 < len(argv):
            accepts = [x.strip() for x in argv[i + 1].split(",") if x.strip()]; i += 2
        elif a == "--location" and i + 1 < len(argv):
            location = argv[i + 1]; i += 2
        elif a in ("-t", "--tag") and i + 1 < len(argv):
            hashtags.append(argv[i + 1]); i += 2
        else:
            description_parts.append(a); i += 1
    if not title:
        console.print("Usage: pergamon classified post --title \"...\" [--price-oz-ag N] [--accepts a,b] [-t tag] \"description\"")
        return 2
    description = " ".join(description_parts).strip()

    ident = get_active()
    if not ident:
        console.print("[red]no active identity.[/red] Create one: pergamon identity create <name>")
        return 1
    nsec = load_nsec(ident.name)

    ev = build_listing_event(
        pubkey_hex=ident.hex_pub,
        title=title, description=description,
        price_oz_ag=price_oz_ag, price_usd=price_usd,
        accepts=accepts or None, location=location, hashtags=hashtags,
    )
    sign_event(ev, nsec)

    relays = _load_relays_from_config()
    console.print(f"[dim]publishing kind {KIND_CLASSIFIED} to {len(relays)} relay(s)[/dim]")
    results = publish(ev, relays)
    any_ok = False
    for url, (ok, msg) in results.items():
        mark = "[green]ok[/green]" if ok else "[red]fail[/red]"
        console.print(f"  [{mark}] {url}  {msg}")
        any_ok = any_ok or ok
    console.print(f"\nlisting id: [cyan]{ev.id}[/cyan]")
    return 0 if any_ok else 1


def _cmd_list(argv: list[str]) -> int:
    tag = None
    limit = DEFAULT_LIMIT
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--tag" and i + 1 < len(argv):
            tag = argv[i + 1]; i += 2
        elif a == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1]); i += 2
        else:
            console.print(f"unknown flag: {a}")
            return 2
    relays = _load_relays_from_config()
    events = fetch_listings(relays, tag=tag, limit=limit)
    if not events:
        console.print("[yellow]no classifieds found. Have you posted any yet?[/yellow]")
        return 0
    for ev in events:
        _print_listing(summarize(ev))
    console.print(f"\n[dim]{len(events)} listing(s) from {len(relays)} relay(s)[/dim]")
    return 0


def _cmd_search(argv: list[str]) -> int:
    if not argv:
        console.print("Usage: pergamon classified search \"query\"")
        return 2
    query = " ".join(argv).lower()
    relays = _load_relays_from_config()
    events = fetch_listings(relays, limit=200)
    hits = []
    for ev in events:
        info = summarize(ev)
        hay = " ".join([info["title"], info["description"], info["location"], " ".join(info["hashtags"])]).lower()
        if query in hay:
            hits.append(info)
    if not hits:
        console.print(f"[yellow]no matches for {query!r}[/yellow]")
        return 0
    for h in hits:
        _print_listing(h)
    console.print(f"\n[dim]{len(hits)} match(es) in {len(events)} listing(s)[/dim]")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        console.print(
            "Usage:\n"
            "  pergamon classified post --title \"...\" [--price-oz-ag N] [--accepts a,b] [-t tag] \"description\"\n"
            "  pergamon classified list [--tag X] [--limit N]\n"
            "  pergamon classified search \"query\""
        )
        return 2
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "post":   return _cmd_post(rest)
    if cmd == "list":   return _cmd_list(rest)
    if cmd == "search": return _cmd_search(rest)
    console.print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
