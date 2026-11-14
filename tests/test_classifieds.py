"""Unit tests for rag.classifieds (NIP-99 kind 30402)."""
from __future__ import annotations

import pytest

from rag.classifieds import (
    KIND_CLASSIFIED,
    build_listing_event,
    summarize,
)
from rag.identity import generate_keypair
from rag.nostr import sign_event, verify_event


def _pub():
    _, _, hex_pub = generate_keypair()
    return hex_pub


# ──────────────────────── build + summarize ─────────────────────────

def test_build_sets_kind_and_d_tag():
    ev = build_listing_event(_pub(), "10 lb apples", "Honeycrisp, pick-up")
    assert ev.kind == KIND_CLASSIFIED
    d_tags = [t for t in ev.tags if t[0] == "d"]
    assert len(d_tags) == 1 and d_tags[0][1]   # non-empty id


def test_build_includes_title_and_description():
    ev = build_listing_event(_pub(), "apples", "Honeycrisp")
    tag_map = {t[0]: t[1:] for t in ev.tags}
    assert tag_map["title"] == ["apples"]
    assert ev.content == "Honeycrisp"


def test_build_price_in_silver():
    ev = build_listing_event(_pub(), "x", "y", price_oz_ag=0.3)
    prices = [t for t in ev.tags if t[0] == "price"]
    assert ["price", "0.3", "oz_ag"] in prices


def test_build_price_in_usd_and_silver_both():
    ev = build_listing_event(_pub(), "x", "y", price_oz_ag=0.3, price_usd=12.50)
    prices = [t for t in ev.tags if t[0] == "price"]
    assert ["price", "0.3", "oz_ag"] in prices
    assert ["price", "12.5", "USD"] in prices


def test_build_accepts_tag():
    ev = build_listing_event(_pub(), "x", "y", accepts=["silver", "barter", "labor"])
    accepts_tag = [t for t in ev.tags if t[0] == "accepts"]
    assert accepts_tag == [["accepts", "silver,barter,labor"]]


def test_build_hashtags_each_get_own_tag():
    ev = build_listing_event(_pub(), "x", "y", hashtags=["apples", "harvest"])
    ts = [t[1] for t in ev.tags if t[0] == "t"]
    assert ts == ["apples", "harvest"]


def test_build_includes_published_at_and_status():
    ev = build_listing_event(_pub(), "x", "y")
    kinds = {t[0] for t in ev.tags}
    assert "published_at" in kinds
    assert ["status", "active"] in ev.tags


def test_summarize_extracts_all_fields():
    ev = build_listing_event(
        _pub(), "20 lb apples", "Honeycrisp, pick-up only",
        price_oz_ag=0.3, price_usd=12.50,
        accepts=["silver", "barter"],
        location="Asheville NC",
        hashtags=["apples", "produce"],
        summary="Bulk apples",
    )
    info = summarize(ev)
    assert info["title"] == "20 lb apples"
    assert info["description"] == "Honeycrisp, pick-up only"
    assert info["price_oz_ag"] == 0.3
    assert info["price_usd"] == 12.50
    assert info["accepts"] == ["silver", "barter"]
    assert info["location"] == "Asheville NC"
    assert info["hashtags"] == ["apples", "produce"]
    assert info["status"] == "active"
    assert info["summary"] == "Bulk apples"


def test_summarize_handles_bare_event():
    ev = build_listing_event(_pub(), "minimal", "no extras")
    info = summarize(ev)
    assert info["title"] == "minimal"
    assert info["price_oz_ag"] is None
    assert info["accepts"] == []
    assert info["location"] == ""
    assert info["hashtags"] == []


def test_build_listing_round_trips_sign_and_verify():
    nsec, _, hex_pub = generate_keypair()
    ev = build_listing_event(
        hex_pub, "signed listing", "full desc",
        price_oz_ag=1.0, accepts=["silver"], hashtags=["test"],
    )
    sign_event(ev, nsec)
    assert verify_event(ev)
