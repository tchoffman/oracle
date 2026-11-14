"""Unit tests for rag.delegation (NIP-26)."""
from __future__ import annotations

import time

import pytest

from rag.delegation import (
    Delegation,
    _token_digest,
    attach_delegation_tag,
    check_event_against_conditions,
    event_authority,
    extract_delegation,
    sign_delegation,
    verify_delegation,
)
from rag.identity import generate_keypair
from rag.nostr import build_event, sign_event


def _kp():
    return generate_keypair()  # (nsec, npub, hex_pub)


# ─────────────────────────── sign / verify ───────────────────────────

def test_sign_and_verify_round_trip():
    alice_nsec, _, _ = _kp()
    _, _, bob_hex = _kp()
    d = sign_delegation(alice_nsec, bob_hex, "kind=1&created_at>1&created_at<9999999999")
    assert verify_delegation(d) is True


def test_verify_rejects_tampered_conditions():
    alice_nsec, _, _ = _kp()
    _, _, bob_hex = _kp()
    d = sign_delegation(alice_nsec, bob_hex, "kind=1&created_at>1&created_at<9999999999")
    d.conditions = "kind=30402&created_at>1&created_at<9999999999"   # swap kind
    assert verify_delegation(d) is False


def test_verify_rejects_wrong_delegator():
    alice_nsec, _, _ = _kp()
    _, _, mallory_hex = _kp()
    _, _, bob_hex = _kp()
    d = sign_delegation(alice_nsec, bob_hex, "kind=1&created_at>1&created_at<9999999999")
    d.delegator_hex = mallory_hex   # claim it was Mallory who signed
    assert verify_delegation(d) is False


def test_malformed_conditions_rejected():
    alice_nsec, _, _ = _kp()
    _, _, bob_hex = _kp()
    with pytest.raises(ValueError):
        sign_delegation(alice_nsec, bob_hex, "garbage")


# ──────────────────────── conditions checker ────────────────────────

def test_conditions_kind_equality():
    _, _, hex_pub = _kp()
    ev = build_event(kind=1, content="x", pubkey_hex=hex_pub)
    ok, _ = check_event_against_conditions(ev, "kind=1")
    assert ok is True
    ok, _ = check_event_against_conditions(ev, "kind=30402")
    assert ok is False


def test_conditions_created_at_range():
    _, _, hex_pub = _kp()
    now = int(time.time())
    ev = build_event(kind=1, content="x", pubkey_hex=hex_pub)
    ev.created_at = now
    ok, _ = check_event_against_conditions(ev, f"created_at>{now - 10}&created_at<{now + 10}")
    assert ok is True
    ok, _ = check_event_against_conditions(ev, f"created_at>{now + 60}")
    assert ok is False


# ──────────────────────── event tag plumbing ────────────────────────

def test_attach_delegation_tag_round_trip():
    alice_nsec, _, alice_hex = _kp()
    bob_nsec, _, bob_hex = _kp()
    conds = f"kind=1&created_at>1&created_at<{int(time.time()) + 3600}"
    d = sign_delegation(alice_nsec, bob_hex, conds)

    ev = build_event(kind=1, content="hi from Bob, on behalf of Alice", pubkey_hex=bob_hex)
    attach_delegation_tag(ev, d)
    sign_event(ev, bob_nsec)

    extracted = extract_delegation(ev)
    assert extracted is not None
    assert extracted.delegator_hex == alice_hex
    assert extracted.sig == d.sig


def test_event_authority_returns_delegator_when_valid():
    alice_nsec, _, alice_hex = _kp()
    bob_nsec, _, bob_hex = _kp()
    conds = f"kind=1&created_at>1&created_at<{int(time.time()) + 3600}"
    d = sign_delegation(alice_nsec, bob_hex, conds)

    ev = build_event(kind=1, content="hi", pubkey_hex=bob_hex)
    attach_delegation_tag(ev, d)
    sign_event(ev, bob_nsec)

    author, deleg = event_authority(ev)
    assert author == alice_hex
    assert deleg is not None


def test_event_authority_falls_back_on_bad_sig():
    alice_nsec, _, alice_hex = _kp()
    bob_nsec, _, bob_hex = _kp()
    conds = f"kind=1&created_at>1&created_at<{int(time.time()) + 3600}"
    d = sign_delegation(alice_nsec, bob_hex, conds)
    d.sig = "00" * 64   # break it

    ev = build_event(kind=1, content="hi", pubkey_hex=bob_hex)
    attach_delegation_tag(ev, d)
    sign_event(ev, bob_nsec)

    author, deleg = event_authority(ev)
    assert author == bob_hex   # falls back to signer
    assert deleg is None


def test_event_authority_falls_back_when_conditions_unmet():
    alice_nsec, _, alice_hex = _kp()
    bob_nsec, _, bob_hex = _kp()
    # Delegation allows only kind=1; event is kind=30402.
    conds = f"kind=1&created_at>1&created_at<{int(time.time()) + 3600}"
    d = sign_delegation(alice_nsec, bob_hex, conds)

    ev = build_event(kind=30402, content="listing", pubkey_hex=bob_hex)
    attach_delegation_tag(ev, d)
    sign_event(ev, bob_nsec)

    author, deleg = event_authority(ev)
    assert author == bob_hex
    assert deleg is None
