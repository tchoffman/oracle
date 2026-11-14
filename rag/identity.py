"""Nostr identity for Pergamon.

A single Pergamon is usually a household, so we support multiple named
identities. Each identity is a secp256k1 keypair; the private key (nsec)
is the secret account ID the owner uses to sign Nostr events.

Storage (all under build/identity/, gitignored):
    <name>.key    — hex-encoded 32-byte private key. Mode 0600.
    <name>.json   — public metadata (npub, display_name, created, nip05).
    active        — plain-text name of the currently active identity.

The private-key file is deliberately *not* passphrase-encrypted on disk.
This is the same tradeoff Pergamon makes everywhere else: the whole
machine's security is the trust boundary. If you want the keys encrypted
at rest, keep them on an external drive you unplug, or use macOS FileVault
/ LUKS on the box itself.

CLI (see `pergamon identity`):
    pergamon identity list                       Show identities + active one
    pergamon identity create <name> [--nip05]    New keypair; mark active
    pergamon identity use <name>                 Switch active identity
    pergamon identity show [--reveal]            Show active; --reveal shows nsec
    pergamon identity export <name> [--path F]   Dump nsec backup to stdout/file
    pergamon identity import <name> <file>       Restore from nsec backup
    pergamon identity delete <name>              Remove (prompts for confirmation)
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import bech32
from coincurve import PrivateKey
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from rag.config import REPO_ROOT

console = Console()

ID_DIR = REPO_ROOT / "build" / "identity"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


@dataclass
class Identity:
    name: str
    npub: str
    hex_pub: str
    display_name: str | None
    created: str
    nip05: str | None

    @property
    def nip05_name(self) -> str:
        """The local-part of the NIP-05 address. Defaults to the identity name."""
        if self.nip05 and "@" in self.nip05:
            return self.nip05.split("@", 1)[0]
        return self.name

    def meta(self) -> dict:
        return {
            "name": self.name,
            "npub": self.npub,
            "hex_pub": self.hex_pub,
            "display_name": self.display_name,
            "created": self.created,
            "nip05": self.nip05,
        }


# ─────────────────────── key encoding helpers ──────────────────────────

def _hex_to_bech32(prefix: str, hex_bytes: str) -> str:
    """Encode a hex-string as nostr-style bech32 (nsec1... or npub1...)."""
    data = bech32.convertbits(bytes.fromhex(hex_bytes), 8, 5)
    return bech32.bech32_encode(prefix, data)


def _bech32_to_hex(expected_prefix: str, s: str) -> str:
    """Decode nostr-style bech32 back to hex. Raises on bad input."""
    hrp, data = bech32.bech32_decode(s)
    if hrp != expected_prefix or data is None:
        raise ValueError(f"not a {expected_prefix}: {s!r}")
    raw = bytes(bech32.convertbits(data, 5, 8, False))
    return raw.hex()


def generate_keypair() -> tuple[str, str, str]:
    """Return (nsec, npub, hex_pub). hex_pub is the x-only 32-byte form Nostr uses."""
    sk = PrivateKey()
    hex_sec = sk.to_hex()
    hex_pub_full = sk.public_key.format(compressed=True).hex()
    # Nostr public keys are x-only — drop the 1-byte sign prefix (0x02 / 0x03).
    hex_pub = hex_pub_full[2:]
    return (
        _hex_to_bech32("nsec", hex_sec),
        _hex_to_bech32("npub", hex_pub),
        hex_pub,
    )


def nsec_to_npub(nsec: str) -> tuple[str, str]:
    """Derive (npub, hex_pub) from an nsec."""
    hex_sec = _bech32_to_hex("nsec", nsec)
    sk = PrivateKey(bytes.fromhex(hex_sec))
    hex_pub = sk.public_key.format(compressed=True).hex()[2:]
    return _hex_to_bech32("npub", hex_pub), hex_pub


# ────────────────────────── storage layer ───────────────────────────────

def _ensure_dir() -> None:
    ID_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(ID_DIR, 0o700)
    except OSError:
        pass


def _validate_name(name: str) -> None:
    if not _NAME_RE.fullmatch(name):
        raise ValueError(
            f"invalid identity name {name!r}: use lowercase letters, digits, - or _, "
            "start with a letter, max 32 chars"
        )


def save_identity(name: str, nsec: str, display_name: str | None = None,
                  nip05: str | None = None) -> Identity:
    _validate_name(name)
    _ensure_dir()
    key_path = ID_DIR / f"{name}.key"
    meta_path = ID_DIR / f"{name}.json"
    if key_path.exists():
        raise FileExistsError(f"identity {name!r} already exists")

    hex_sec = _bech32_to_hex("nsec", nsec)
    npub, hex_pub = nsec_to_npub(nsec)
    ident = Identity(
        name=name, npub=npub, hex_pub=hex_pub,
        display_name=display_name,
        created=datetime.now().isoformat(timespec="seconds"),
        nip05=nip05,
    )
    # Write key first with restrictive permissions.
    key_path.write_text(hex_sec)
    os.chmod(key_path, 0o600)
    meta_path.write_text(json.dumps(ident.meta(), indent=2))
    return ident


def load_identity(name: str) -> Identity:
    _validate_name(name)
    meta_path = ID_DIR / f"{name}.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"no identity: {name}")
    meta = json.loads(meta_path.read_text())
    return Identity(
        name=meta["name"], npub=meta["npub"], hex_pub=meta["hex_pub"],
        display_name=meta.get("display_name"),
        created=meta["created"],
        nip05=meta.get("nip05"),
    )


def load_nsec(name: str) -> str:
    key_path = ID_DIR / f"{name}.key"
    if not key_path.exists():
        raise FileNotFoundError(f"no key for identity: {name}")
    hex_sec = key_path.read_text().strip()
    return _hex_to_bech32("nsec", hex_sec)


def list_identities() -> list[Identity]:
    if not ID_DIR.exists():
        return []
    out = []
    for p in sorted(ID_DIR.glob("*.json")):
        try:
            out.append(load_identity(p.stem))
        except Exception:
            continue
    return out


def set_active(name: str) -> None:
    # Confirm identity exists first.
    load_identity(name)
    (ID_DIR / "active").write_text(name)


def get_active() -> Identity | None:
    marker = ID_DIR / "active"
    if not marker.exists():
        return None
    name = marker.read_text().strip()
    try:
        return load_identity(name)
    except FileNotFoundError:
        return None


def delete_identity(name: str) -> None:
    _validate_name(name)
    for suffix in (".key", ".json"):
        p = ID_DIR / f"{name}{suffix}"
        if p.exists():
            p.unlink()
    marker = ID_DIR / "active"
    if marker.exists() and marker.read_text().strip() == name:
        marker.unlink()


# ──────────────────────────── CLI ──────────────────────────────────────

def _print_list() -> None:
    idents = list_identities()
    active = get_active()
    if not idents:
        console.print("[yellow]No identities. Create one with:[/yellow] pergamon identity create <name>")
        return
    table = Table(title="Pergamon identities")
    table.add_column("active")
    table.add_column("name")
    table.add_column("npub")
    table.add_column("nip05")
    table.add_column("created")
    for i in idents:
        is_active = "*" if active and active.name == i.name else ""
        table.add_row(is_active, i.name, i.npub, i.nip05 or "", i.created)
    console.print(table)


def _cmd_create(argv: list[str]) -> int:
    if not argv:
        console.print("Usage: pergamon identity create <name> [--nip05 user@domain] [--display 'Display Name']")
        return 2
    name = argv[0]
    nip05 = None
    display = None
    i = 1
    while i < len(argv):
        if argv[i] == "--nip05" and i + 1 < len(argv):
            nip05 = argv[i + 1]; i += 2
        elif argv[i] == "--display" and i + 1 < len(argv):
            display = argv[i + 1]; i += 2
        else:
            console.print(f"unknown flag: {argv[i]}")
            return 2
    nsec, npub, _ = generate_keypair()
    try:
        ident = save_identity(name, nsec, display_name=display, nip05=nip05)
    except (ValueError, FileExistsError) as e:
        console.print(f"[red]{e}[/red]")
        return 1
    set_active(name)
    console.print(f"[green]Created[/green] identity [bold]{ident.name}[/bold]")
    console.print(f"  npub: [cyan]{ident.npub}[/cyan]")
    console.print(f"  stored at: {ID_DIR}/{name}.key (mode 0600)")
    if ident.nip05:
        console.print(f"  nip05: {ident.nip05}")
    console.print("\n[yellow]Back up your nsec:[/yellow]")
    console.print(f"  pergamon identity export {name}")
    return 0


def _cmd_show(argv: list[str]) -> int:
    reveal = "--reveal" in argv
    rest = [a for a in argv if a != "--reveal"]
    name = rest[0] if rest else None
    if name:
        try:
            ident = load_identity(name)
        except FileNotFoundError:
            console.print(f"[red]no identity: {name}[/red]")
            return 1
    else:
        ident = get_active()
        if not ident:
            console.print("[yellow]no active identity[/yellow]")
            return 1
    console.print(f"name:    {ident.name}")
    console.print(f"npub:    {ident.npub}")
    console.print(f"hex_pub: {ident.hex_pub}")
    if ident.display_name:
        console.print(f"display: {ident.display_name}")
    if ident.nip05:
        console.print(f"nip05:   {ident.nip05}")
    console.print(f"created: {ident.created}")
    if reveal:
        console.print(f"\n[red]nsec (KEEP SECRET):[/red] [bold]{load_nsec(ident.name)}[/bold]")
    else:
        console.print("\n[dim](nsec hidden. Pass --reveal to show.)[/dim]")
    return 0


def _cmd_use(argv: list[str]) -> int:
    if not argv:
        console.print("Usage: pergamon identity use <name>")
        return 2
    try:
        set_active(argv[0])
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    console.print(f"[green]active identity →[/green] {argv[0]}")
    return 0


def _cmd_export(argv: list[str]) -> int:
    if not argv:
        console.print("Usage: pergamon identity export <name> [--path FILE]")
        return 2
    name = argv[0]
    out_path = None
    if len(argv) >= 3 and argv[1] == "--path":
        out_path = Path(argv[2])
    try:
        nsec = load_nsec(name)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    if out_path:
        out_path.write_text(nsec + "\n")
        os.chmod(out_path, 0o600)
        console.print(f"[green]wrote {out_path} (mode 0600)[/green]")
    else:
        # Treat stdout as visible — warn once.
        console.print("[red]Store this somewhere safe. Anyone with it owns the identity:[/red]")
        print(nsec)
    return 0


def _cmd_import(argv: list[str]) -> int:
    if len(argv) < 2:
        console.print("Usage: pergamon identity import <name> <file>")
        return 2
    name, path = argv[0], Path(argv[1])
    if not path.exists():
        console.print(f"[red]no such file: {path}[/red]")
        return 1
    nsec = path.read_text().strip()
    try:
        ident = save_identity(name, nsec)
    except (ValueError, FileExistsError) as e:
        console.print(f"[red]{e}[/red]")
        return 1
    console.print(f"[green]imported[/green] {ident.name} — npub {ident.npub}")
    return 0


def _cmd_delete(argv: list[str]) -> int:
    if not argv:
        console.print("Usage: pergamon identity delete <name>")
        return 2
    name = argv[0]
    try:
        load_identity(name)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return 1
    if not Confirm.ask(f"Delete identity '{name}' and its private key?", default=False):
        console.print("[yellow]aborted[/yellow]")
        return 1
    delete_identity(name)
    console.print(f"[green]deleted[/green] {name}")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "ls"):
        _print_list()
        return 0
    cmd = argv[0]
    rest = argv[1:]
    dispatch = {
        "create": _cmd_create,
        "show":   _cmd_show,
        "use":    _cmd_use,
        "export": _cmd_export,
        "import": _cmd_import,
        "delete": _cmd_delete,
    }
    if cmd in dispatch:
        return dispatch[cmd](rest)
    console.print(
        "Usage:\n"
        "  pergamon identity list\n"
        "  pergamon identity create <name> [--nip05 user@domain] [--display 'Name']\n"
        "  pergamon identity show [<name>] [--reveal]\n"
        "  pergamon identity use <name>\n"
        "  pergamon identity export <name> [--path FILE]\n"
        "  pergamon identity import <name> <file>\n"
        "  pergamon identity delete <name>"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
