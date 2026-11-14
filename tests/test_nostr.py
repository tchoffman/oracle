"""Unit tests for rag.nostr.

Covers event building + canonical serialization + sign/verify + publish
over a mocked WebSocket. No live relay needed.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag import nostr
from rag.identity import generate_keypair
from rag.nostr import (
    Event,
    _compute_id,
    build_event,
    publish,
    sign_event,
    verify_event,
)


# ───────────────────────── sign / verify ─────────────────────────────

def _fresh_identity():
    nsec, npub, hex_pub = generate_keypair()
    return nsec, npub, hex_pub


def test_event_id_is_deterministic_for_same_timestamp():
    _, _, hex_pub = _fresh_identity()
    ev = Event(kind=1, content="hello", pubkey=hex_pub, created_at=1700000000)
    first = _compute_id(ev)
    second = _compute_id(ev)
    assert first == second


def test_sign_event_fills_id_and_sig():
    nsec, _, hex_pub = _fresh_identity()
    ev = build_event(kind=1, content="hello world", pubkey_hex=hex_pub)
    signed = sign_event(ev, nsec, aux_rand=b"\x00" * 32)
    assert len(signed.id) == 64
    assert len(signed.sig) == 128


def test_verify_event_round_trip():
    nsec, _, hex_pub = _fresh_identity()
    ev = sign_event(
        build_event(kind=1, content="verify me", pubkey_hex=hex_pub),
        nsec,
    )
    assert verify_event(ev) is True


def test_verify_detects_tampered_content():
    nsec, _, hex_pub = _fresh_identity()
    ev = sign_event(
        build_event(kind=1, content="original", pubkey_hex=hex_pub),
        nsec,
    )
    ev.content = "tampered"
    assert verify_event(ev) is False


def test_verify_detects_wrong_pubkey():
    nsec_a, _, hex_pub_a = _fresh_identity()
    _, _, hex_pub_b = _fresh_identity()
    ev = sign_event(
        build_event(kind=1, content="x", pubkey_hex=hex_pub_a),
        nsec_a,
    )
    ev.pubkey = hex_pub_b
    # id is wrong now (pubkey embedded in serialization), so verify fails
    assert verify_event(ev) is False


def test_event_tags_are_preserved_in_serialization():
    _, _, hex_pub = _fresh_identity()
    ev = Event(
        kind=30402, content="listing",
        pubkey=hex_pub, created_at=1700000000,
        tags=[["d", "unique-id"], ["t", "classified"]],
    )
    serialized = json.loads(ev.serialize_for_id())
    assert serialized[4] == [["d", "unique-id"], ["t", "classified"]]


# ─────────────────────────── publish (mocked) ────────────────────────

class _FakeWS:
    """Minimal async context manager + send/recv mimicking websockets.connect."""

    def __init__(self, ok_response_json: str):
        self._ok = ok_response_json
        self.sent: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def send(self, raw: str):
        self.sent.append(raw)

    async def recv(self) -> str:
        return self._ok


def _mock_connect_factory(ok_response_json: str):
    """Build an awaitable mock that behaves like `websockets.connect(...)`."""
    fake = _FakeWS(ok_response_json)

    def connect(url, **kwargs):
        return fake

    return connect, fake


def test_publish_sends_event_and_reports_ok(monkeypatch):
    nsec, _, hex_pub = _fresh_identity()
    ev = sign_event(build_event(1, "hi", hex_pub), nsec)

    ok_json = json.dumps(["OK", ev.id, True, ""])
    connect_fn, fake = _mock_connect_factory(ok_json)
    monkeypatch.setattr(nostr.websockets, "connect", connect_fn)

    results = publish(ev, ["ws://fake/"])
    assert results["ws://fake/"] == (True, "")
    assert len(fake.sent) == 1
    sent = json.loads(fake.sent[0])
    assert sent[0] == "EVENT"
    assert sent[1]["id"] == ev.id
    assert sent[1]["content"] == "hi"


def test_publish_reports_rejection(monkeypatch):
    nsec, _, hex_pub = _fresh_identity()
    ev = sign_event(build_event(1, "nope", hex_pub), nsec)

    ok_json = json.dumps(["OK", ev.id, False, "blocked: spam"])
    connect_fn, _ = _mock_connect_factory(ok_json)
    monkeypatch.setattr(nostr.websockets, "connect", connect_fn)

    results = publish(ev, ["ws://fake/"])
    accepted, msg = results["ws://fake/"]
    assert accepted is False
    assert "blocked" in msg


def test_publish_reports_connection_error(monkeypatch):
    nsec, _, hex_pub = _fresh_identity()
    ev = sign_event(build_event(1, "hi", hex_pub), nsec)

    def connect_fail(url, **kwargs):
        raise ConnectionError("relay unreachable")

    monkeypatch.setattr(nostr.websockets, "connect", connect_fail)
    results = publish(ev, ["ws://offline/"])
    accepted, msg = results["ws://offline/"]
    assert accepted is False
    assert "ConnectionError" in msg or "unreachable" in msg


# ──────────────────────── relay config helpers ───────────────────────

def test_relay_config_default_when_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(nostr, "INSTALL_LOCAL_PATH", tmp_path / "install.local.yaml")
    relays = nostr._load_relays_from_config()
    assert relays == [nostr.DEFAULT_RELAY]


def test_relay_config_save_and_load(tmp_path, monkeypatch):
    path = tmp_path / "install.local.yaml"
    monkeypatch.setattr(nostr, "INSTALL_LOCAL_PATH", path)
    nostr._save_relays(["ws://a/", "ws://b/"])
    assert nostr._load_relays_from_config() == ["ws://a/", "ws://b/"]
