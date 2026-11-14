"""Unit tests for rag.identity.

Pure crypto + file-storage logic. Uses tmp_path for the key directory so
tests never touch build/identity.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from rag import identity
from rag.identity import (
    _bech32_to_hex,
    _hex_to_bech32,
    delete_identity,
    generate_keypair,
    get_active,
    list_identities,
    load_identity,
    load_nsec,
    nsec_to_npub,
    save_identity,
    set_active,
)


@pytest.fixture
def tmp_id_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, "ID_DIR", tmp_path)
    return tmp_path


# ───────────────────────── crypto round-trip ──────────────────────────

def test_generate_keypair_shape():
    nsec, npub, hex_pub = generate_keypair()
    assert nsec.startswith("nsec1")
    assert npub.startswith("npub1")
    assert len(hex_pub) == 64, "x-only pubkey is 32 bytes = 64 hex chars"


def test_bech32_round_trip():
    hex_in = "0123456789abcdef" * 4
    s = _hex_to_bech32("npub", hex_in)
    hex_out = _bech32_to_hex("npub", s)
    assert hex_out == hex_in


def test_nsec_to_npub_is_deterministic():
    nsec, npub_a, hex_a = generate_keypair()
    npub_b, hex_b = nsec_to_npub(nsec)
    assert npub_a == npub_b
    assert hex_a == hex_b


def test_bech32_wrong_prefix_rejected():
    _, npub, _ = generate_keypair()
    with pytest.raises(ValueError):
        _bech32_to_hex("nsec", npub)   # npub cannot decode as nsec


# ───────────────────────── storage layer ──────────────────────────────

def test_save_and_load(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    ident = save_identity("alice", nsec, display_name="Alice",
                          nip05="alice@pergamon.local")
    reloaded = load_identity("alice")
    assert reloaded.name == "alice"
    assert reloaded.npub == ident.npub
    assert reloaded.nip05 == "alice@pergamon.local"


def test_save_sets_key_permissions(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    save_identity("bob", nsec)
    key_file = tmp_id_dir / "bob.key"
    mode = key_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_duplicate_name_rejected(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    save_identity("carol", nsec)
    with pytest.raises(FileExistsError):
        save_identity("carol", nsec)


def test_invalid_names_rejected(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    for bad in ("Alice", "1starts_with_digit", "has spaces", "very" + "long" * 20):
        with pytest.raises(ValueError):
            save_identity(bad, nsec)


def test_load_nsec_round_trips(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    save_identity("dave", nsec)
    assert load_nsec("dave") == nsec


def test_list_identities(tmp_id_dir):
    for n in ("eve", "frank", "ginny"):
        nsec, _, _ = generate_keypair()
        save_identity(n, nsec)
    names = [i.name for i in list_identities()]
    assert names == ["eve", "frank", "ginny"]


def test_active_pointer(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    save_identity("hank", nsec)
    nsec2, _, _ = generate_keypair()
    save_identity("iris", nsec2)
    assert get_active() is None
    set_active("iris")
    assert get_active().name == "iris"
    set_active("hank")
    assert get_active().name == "hank"


def test_set_active_rejects_unknown(tmp_id_dir):
    with pytest.raises(FileNotFoundError):
        set_active("nobody")


def test_delete_clears_active(tmp_id_dir):
    nsec, _, _ = generate_keypair()
    save_identity("jules", nsec)
    set_active("jules")
    delete_identity("jules")
    assert get_active() is None
    assert not (tmp_id_dir / "jules.key").exists()


def test_import_from_nsec(tmp_id_dir):
    """Round-trip: generate → save → export → delete → import → match."""
    nsec, npub_before, _ = generate_keypair()
    save_identity("kate", nsec)
    delete_identity("kate")
    # Import under a different name (matches CLI UX).
    reimported = save_identity("liam", nsec)
    assert reimported.npub == npub_before


# ───────────────────────── NIP-05 endpoint ────────────────────────────

def test_nip05_endpoint(tmp_id_dir):
    # Create an identity, hit the endpoint via TestClient.
    nsec, _, hex_pub = generate_keypair()
    save_identity("mia", nsec, nip05="mia@example.local")

    from fastapi.testclient import TestClient
    from rag.web import app
    client = TestClient(app, raise_server_exceptions=False)

    r = client.get("/.well-known/nostr.json?name=mia")
    assert r.status_code == 200
    body = r.json()
    assert body["names"]["mia"] == hex_pub

    r = client.get("/.well-known/nostr.json?name=nobody")
    assert r.status_code == 200
    assert r.json()["names"] == {}
