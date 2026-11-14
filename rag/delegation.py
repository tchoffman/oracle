"""NIP-26 delegation — "Alice allows Bob to post on her behalf, bounded."

Alice signs a token authorizing Bob's pubkey + conditions (kind ranges,
time bounds). Bob publishes as himself but attaches a `delegation` tag
containing Alice's signature. Conforming clients display the event as
from Alice; reputation flows to her npub; the audit trail still shows
Bob (the host, the paper-form scanner, etc.) did the signing.

Spec: https://github.com/nostr-protocol/nips/blob/master/26.md

Token format:
    nostr:delegation:<delegatee_hex_pubkey>:<conditions>

Signature:  BIP-340 schnorr over sha256(token) by the delegator (Alice).

Conditions grammar: &-joined query-string of `key=value` or `key>value` or
`key<value`. Standard keys: `kind`, `created_at`. Example:

    kind=1&created_at>1700000000&created_at<1800000000

Event tag attached by the delegatee:
    ["delegation", <delegator_hex>, <conditions>, <hex_sig>]
"""
from __future__ import annotations

import hashlib
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from coincurve import PrivateKey
from coincurve.keys import PublicKeyXOnly
from rich.console import Console

from rag.identity import (
    _bech32_to_hex,
    get_active,
    load_identity,
    load_nsec,
)
from rag.nostr import Event

console = Console()

_COND = re.compile(r"^(kind|created_at)([=<>])(\d+)$")


@dataclass
class Delegation:
    delegator_hex: str   # Alice
    delegatee_hex: str   # Bob
    conditions: str
    sig: str


# ───────────────────────── token + signing ───────────────────────────

def _token(delegatee_hex: str, conditions: str) -> str:
    return f"nostr:delegation:{delegatee_hex}:{conditions}"


def _token_digest(delegatee_hex: str, conditions: str) -> bytes:
    """NIP-26 signs sha256 of the token string."""
    return hashlib.sha256(_token(delegatee_hex, conditions).encode("utf-8")).digest()


def sign_delegation(delegator_nsec: str, delegatee_hex: str, conditions: str,
                    aux_rand: bytes | None = None) -> Delegation:
    """Delegator signs an authorization for delegatee + conditions. Returns Delegation."""
    _validate_conditions(conditions)
    hex_sec = _bech32_to_hex("nsec", delegator_nsec)
    sk = PrivateKey(bytes.fromhex(hex_sec))
    delegator_hex = sk.public_key.format(compressed=True).hex()[2:]
    digest = _token_digest(delegatee_hex, conditions)
    aux = aux_rand if aux_rand is not None else b""
    sig = sk.sign_schnorr(digest, aux).hex()
    return Delegation(
        delegator_hex=delegator_hex,
        delegatee_hex=delegatee_hex,
        conditions=conditions,
        sig=sig,
    )


def verify_delegation(d: Delegation) -> bool:
    """Check that the sig is valid for (delegatee, conditions) under the delegator's key."""
    _validate_conditions(d.conditions)
    try:
        pk = PublicKeyXOnly(bytes.fromhex(d.delegator_hex))
        return pk.verify(bytes.fromhex(d.sig), _token_digest(d.delegatee_hex, d.conditions))
    except Exception:
        return False


# ───────────────────────── conditions parser ─────────────────────────

def _validate_conditions(conditions: str) -> None:
    if not conditions:
        raise ValueError("conditions must be non-empty")
    for clause in conditions.split("&"):
        if not _COND.fullmatch(clause):
            raise ValueError(f"bad condition clause {clause!r}")


def check_event_against_conditions(event: Event, conditions: str) -> tuple[bool, str]:
    """Return (ok, reason) for whether the event satisfies the conditions string."""
    _validate_conditions(conditions)
    for clause in conditions.split("&"):
        m = _COND.fullmatch(clause)
        assert m is not None
        key, op, value = m.group(1), m.group(2), int(m.group(3))
        actual = {"kind": event.kind, "created_at": event.created_at}[key]
        if op == "=" and actual != value:
            return False, f"{key}={actual}, requires {clause}"
        if op == ">" and not (actual > value):
            return False, f"{key}={actual}, requires {clause}"
        if op == "<" and not (actual < value):
            return False, f"{key}={actual}, requires {clause}"
    return True, "ok"


# ────────────────────────── event helpers ────────────────────────────

def attach_delegation_tag(event: Event, d: Delegation) -> Event:
    """Mutate event.tags to include the NIP-26 delegation tag. Returns the event."""
    tag = ["delegation", d.delegator_hex, d.conditions, d.sig]
    event.tags = [t for t in event.tags if not (t and t[0] == "delegation")]
    event.tags.append(tag)
    return event


def extract_delegation(event: Event) -> Delegation | None:
    for t in event.tags:
        if t and t[0] == "delegation" and len(t) >= 4:
            return Delegation(delegator_hex=t[1], conditions=t[2], sig=t[3],
                              delegatee_hex=event.pubkey)
    return None


def event_authority(event: Event) -> tuple[str, Delegation | None]:
    """Return (effective_author_pubkey, delegation). The effective author is the
    delegator when a valid delegation is attached AND the event satisfies its
    conditions; otherwise it's just the event signer.
    """
    d = extract_delegation(event)
    if not d:
        return event.pubkey, None
    if not verify_delegation(d):
        return event.pubkey, None
    ok, _reason = check_event_against_conditions(event, d.conditions)
    if not ok:
        return event.pubkey, None
    return d.delegator_hex, d


# ────────────────────────────── CLI ──────────────────────────────────

def _parse_until(s: str) -> int:
    """Accept '7d' / '30d' / '12h' / ISO date / unix timestamp. Returns unix int."""
    s = s.strip()
    now = int(time.time())
    if s.endswith("d") and s[:-1].isdigit():
        return now + int(s[:-1]) * 86400
    if s.endswith("h") and s[:-1].isdigit():
        return now + int(s[:-1]) * 3600
    if s.isdigit():
        return int(s)
    try:
        return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        raise ValueError(f"can't parse --until: {s!r} (try 7d, 24h, ISO date, or unix timestamp)")


def _cmd_create(argv: list[str]) -> int:
    """pergamon delegation create --to NPUB [--kind N]+ [--until 30d]"""
    delegatee_npub = None
    kinds: list[int] = []
    until: int | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--to" and i + 1 < len(argv):
            delegatee_npub = argv[i + 1]; i += 2
        elif a == "--kind" and i + 1 < len(argv):
            kinds.append(int(argv[i + 1])); i += 2
        elif a == "--until" and i + 1 < len(argv):
            until = _parse_until(argv[i + 1]); i += 2
        else:
            console.print(f"unknown flag: {a}")
            return 2
    if not delegatee_npub:
        console.print("Usage: pergamon delegation create --to <npub> [--kind N]+ [--until 30d]")
        return 2
    try:
        delegatee_hex = _bech32_to_hex("npub", delegatee_npub)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    clauses: list[str] = []
    for k in kinds:
        clauses.append(f"kind={k}")
    clauses.append(f"created_at>{int(time.time()) - 60}")   # "from a minute ago" to give slack
    if until:
        clauses.append(f"created_at<{until}")
    conditions = "&".join(clauses)

    ident = get_active()
    if not ident:
        console.print("[red]no active identity.[/red] Create one: pergamon identity create <name>")
        return 1
    d = sign_delegation(load_nsec(ident.name), delegatee_hex, conditions)
    console.print(f"[green]delegation signed[/green] from {ident.npub}")
    console.print(f"  to:         {delegatee_npub}")
    console.print(f"  conditions: {d.conditions}")
    console.print(f"  sig:        {d.sig}")
    console.print()
    console.print("Share this tag with the delegatee — they attach it to events they post on your behalf:")
    console.print(f'  ["delegation", "{d.delegator_hex}", "{d.conditions}", "{d.sig}"]')
    return 0


def _cmd_verify(argv: list[str]) -> int:
    """pergamon delegation verify DELEGATOR_HEX DELEGATEE_HEX CONDITIONS SIG"""
    if len(argv) != 4:
        console.print("Usage: pergamon delegation verify <delegator_hex> <delegatee_hex> <conditions> <sig>")
        return 2
    d = Delegation(delegator_hex=argv[0], delegatee_hex=argv[1],
                   conditions=argv[2], sig=argv[3])
    ok = verify_delegation(d)
    console.print(f"[{'green' if ok else 'red'}]{'valid' if ok else 'INVALID'}[/]")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if not argv:
        console.print(
            "Usage:\n"
            "  pergamon delegation create --to <npub> [--kind N]+ [--until 30d]\n"
            "  pergamon delegation verify <delegator_hex> <delegatee_hex> <conditions> <sig>"
        )
        return 2
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "create": return _cmd_create(rest)
    if cmd == "verify": return _cmd_verify(rest)
    console.print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
