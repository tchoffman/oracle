"""Tests for the /identity + /api/identity/* endpoints."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag import identity, nostr
from rag.web import app


@pytest.fixture
def seeded_identity(tmp_path, monkeypatch):
    """One active identity in a tmp dir; relay set to an unreachable URL."""
    monkeypatch.setattr(identity, "ID_DIR", tmp_path)
    monkeypatch.setattr(nostr, "INSTALL_LOCAL_PATH", tmp_path / "install.local.yaml")
    nsec, _, _ = identity.generate_keypair()
    identity.save_identity("alice", nsec, display_name="Alice",
                           nip05="alice@pergamon.local")
    identity.set_active("alice")
    return TestClient(app, raise_server_exceptions=False)


def test_identity_page_renders(seeded_identity):
    r = seeded_identity.get("/identity")
    assert r.status_code == 200
    assert "alice" in r.text
    assert "npub" in r.text.lower()


def test_active_endpoint(seeded_identity):
    r = seeded_identity.get("/api/identity/active")
    assert r.status_code == 200
    data = r.json()
    assert data["active"]["name"] == "alice"
    assert data["active"]["nip05"] == "alice@pergamon.local"


def test_switch_to_unknown_identity_returns_404(seeded_identity):
    r = seeded_identity.post("/api/identity/use", json={"name": "nobody"})
    assert r.status_code == 404


def test_switch_active(seeded_identity, tmp_path, monkeypatch):
    # Create a second identity in the same ID_DIR.
    nsec2, _, _ = identity.generate_keypair()
    identity.save_identity("bob", nsec2)
    r = seeded_identity.post("/api/identity/use", json={"name": "bob"})
    assert r.status_code == 200
    assert r.json()["active"]["name"] == "bob"


def test_profile_publish_returns_event_id(seeded_identity, monkeypatch):
    """Even with no reachable relay, the endpoint should sign + report per-relay failure."""
    # Mock websockets.connect so publish reports a known result.
    import json

    class _FakeWS:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def send(self, raw): self.sent = raw
        async def recv(self):
            # The relay's OK response needs the event id. Tests don't know it
            # ahead of time; emit something that keeps the publish path going
            # and then yield a fake OK for whatever id came in.
            import json as _j
            sent = _j.loads(self.sent)
            event = sent[1]
            return _j.dumps(["OK", event["id"], True, ""])

    def connect(url, **kwargs):
        return _FakeWS()

    monkeypatch.setattr(nostr.websockets, "connect", connect)

    r = seeded_identity.post(
        "/api/identity/profile",
        json={"display_name": "Alice Example", "about": "field notes"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["event_id"]) == 64
    assert "display_name" in data["metadata"]


def test_profile_publish_rejects_when_no_active(seeded_identity, monkeypatch):
    # Clear active.
    marker = identity.ID_DIR / "active"
    if marker.exists():
        marker.unlink()
    r = seeded_identity.post("/api/identity/profile", json={"display_name": "x"})
    assert r.status_code == 400


def test_profile_publish_rejects_empty_payload(seeded_identity):
    r = seeded_identity.post("/api/identity/profile", json={})
    assert r.status_code == 400
