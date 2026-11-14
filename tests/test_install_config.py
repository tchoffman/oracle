"""Unit tests for rag.install_config.

These tests touch only local files — no network. They validate that the
catalog parses correctly, presets merge as expected, and user overrides
produce the right effective config.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rag import install_config
from rag.install_config import (
    _merge_enable,
    available_presets,
    item_size_mb,
    load_catalog,
    load_effective_config,
    load_yaml,
    save_local_config,
)


# ─────────────────────────────── catalog ────────────────────────────────

def test_catalog_loads_and_has_items():
    catalog = load_catalog()
    assert len(catalog) >= 10, "catalog should have many items"
    # Spot-check Wikipedia is there with expected shape.
    assert "wikipedia" in catalog
    wiki = catalog["wikipedia"]
    assert wiki["fetcher"] == "kiwix-zim"
    assert "kiwix" in wiki
    assert "prefix_by_variant" in wiki["kiwix"]
    assert "simple" in wiki["kiwix"]["prefix_by_variant"]


def test_catalog_items_have_fetcher():
    catalog = load_catalog()
    allowed_fetchers = {
        "kiwix-zim", "archive-pdf", "gutenberg",
        "stackexchange", "mirror-site", "osmand-region",
    }
    for item_id, item in catalog.items():
        assert item.get("fetcher") in allowed_fetchers, (
            f"{item_id}: unknown fetcher {item.get('fetcher')!r}"
        )


def test_catalog_items_have_shelf():
    catalog = load_catalog()
    for item_id, item in catalog.items():
        assert item.get("shelf"), f"{item_id} has no shelf"


def test_kiwix_items_have_project_and_prefixes():
    catalog = load_catalog()
    for item_id, item in catalog.items():
        if item["fetcher"] != "kiwix-zim":
            continue
        kcfg = item.get("kiwix") or {}
        assert "project" in kcfg, f"{item_id}: missing kiwix.project"
        assert "prefix_by_variant" in kcfg, f"{item_id}: missing prefix_by_variant"
        assert kcfg["prefix_by_variant"], f"{item_id}: empty prefix_by_variant"


def test_archive_pdf_items_have_url():
    catalog = load_catalog()
    for item_id, item in catalog.items():
        if item["fetcher"] != "archive-pdf":
            continue
        assert item.get("archive", {}).get("url"), f"{item_id}: missing archive.url"


# ─────────────────────────────── presets ────────────────────────────────

def test_available_presets():
    presets = available_presets()
    names = {p["file"] for p in presets}
    assert names == {"minimal", "default", "comprehensive"}


def test_presets_reference_known_items():
    catalog = load_catalog()
    for p in available_presets():
        data = load_yaml(install_config.PRESETS_DIR / f"{p['file']}.yaml")
        enable = data.get("enable") or {}
        for item_id in enable:
            assert item_id in catalog, (
                f"preset {p['file']} references unknown item: {item_id}"
            )


def test_default_preset_sane():
    data = load_yaml(install_config.PRESETS_DIR / "default.yaml")
    enable = data.get("enable") or {}
    # Default must include Wikipedia in some form.
    assert "wikipedia" in enable


# ──────────────────────────────── merge ─────────────────────────────────

def test_merge_enable_adds_new_items():
    preset = {"wikipedia": {"variant": "simple"}}
    override = {"ifixit": {}}
    merged = _merge_enable(preset, override)
    assert "wikipedia" in merged
    assert "ifixit" in merged


def test_merge_enable_changes_option():
    preset = {"wikipedia": {"variant": "simple"}}
    override = {"wikipedia": {"variant": "nopic"}}
    merged = _merge_enable(preset, override)
    assert merged["wikipedia"]["variant"] == "nopic"


def test_merge_enable_removes_with_none():
    preset = {"wikipedia": {"variant": "simple"}, "ifixit": {}}
    override = {"ifixit": None}
    merged = _merge_enable(preset, override)
    assert "wikipedia" in merged
    assert "ifixit" not in merged


def test_merge_enable_preserves_existing_options():
    preset = {"stackexchange": {"sites": ["outdoors", "gardening"]}}
    # Override that only tweaks sites — should replace, not append.
    override = {"stackexchange": {"sites": ["cooking"]}}
    merged = _merge_enable(preset, override)
    assert merged["stackexchange"]["sites"] == ["cooking"]


# ─────────────────────────── effective config ───────────────────────────

def test_load_effective_uses_preset(tmp_path, monkeypatch):
    """When install.local.yaml specifies a preset, effective matches it."""
    _redirect_config(monkeypatch, tmp_path)
    _write(tmp_path / "install.local.yaml", {"preset": "minimal"})

    eff = load_effective_config()
    assert eff["preset"] == "minimal"
    # Minimal preset should include Wikipedia Simple
    assert "wikipedia" in eff["enable"]


def test_load_effective_applies_overrides(tmp_path, monkeypatch):
    _redirect_config(monkeypatch, tmp_path)
    _write(
        tmp_path / "install.local.yaml",
        {
            "preset": "default",
            "overrides": {
                "wikipedia": {"variant": "nopic"},
                "wikivoyage": None,  # remove it
            },
        },
    )
    eff = load_effective_config()
    assert eff["enable"]["wikipedia"]["variant"] == "nopic"
    assert "wikivoyage" not in eff["enable"]


# ─────────────────────────────── models ─────────────────────────────────

def test_model_catalog_has_both_roles():
    from rag.install_config import load_model_catalog
    cat = load_model_catalog()
    assert "primary" in cat and "embedding" in cat
    assert len(cat["primary"]) >= 2, "catalog should offer multiple primary models"
    assert len(cat["embedding"]) >= 2, "catalog should offer multiple embedding models"


def test_model_catalog_entries_have_ollama_tag():
    from rag.install_config import load_model_catalog
    cat = load_model_catalog()
    for role in ("primary", "embedding"):
        for mid, entry in cat[role].items():
            assert "ollama_tag" in entry, f"{role}/{mid} missing ollama_tag"
            assert "size_mb" in entry, f"{role}/{mid} missing size_mb"


def test_effective_config_includes_preset_models():
    eff = load_effective_config()  # whatever the current env has
    assert "models" in eff
    # Models should be a dict with at least primary + embedding when a preset
    # declares them. All current presets declare both.
    assert "primary" in eff["models"]
    assert "embedding" in eff["models"]


def test_effective_config_applies_model_override(tmp_path, monkeypatch):
    _redirect_config(monkeypatch, tmp_path)
    _write(
        tmp_path / "install.local.yaml",
        {
            "preset": "default",
            "models": {"primary": "qwen2.5-7b-q4"},  # override the default's llama
        },
    )
    eff = load_effective_config()
    assert eff["models"]["primary"] == "qwen2.5-7b-q4"
    # Embedding comes from the preset since we didn't override it.
    assert eff["models"]["embedding"] == "nomic-embed-text"


def test_presets_reference_known_models():
    from rag.install_config import load_model_catalog
    cat = load_model_catalog()
    for p in available_presets():
        data = load_yaml(install_config.PRESETS_DIR / f"{p['file']}.yaml")
        models = data.get("models") or {}
        if "primary" in models:
            assert models["primary"] in cat["primary"], (
                f"preset {p['file']} references unknown primary model: {models['primary']}"
            )
        if "embedding" in models:
            assert models["embedding"] in cat["embedding"], (
                f"preset {p['file']} references unknown embedding model: {models['embedding']}"
            )


def test_save_local_config_persists_models(tmp_path, monkeypatch):
    _redirect_config(monkeypatch, tmp_path)
    from rag.install_config import save_local_config
    save_local_config("default", models={"primary": "qwen2.5-14b-q4"})
    loaded = load_yaml(tmp_path / "install.local.yaml")
    assert loaded["models"]["primary"] == "qwen2.5-14b-q4"


# ─────────────────────────────── sizes ──────────────────────────────────

def test_item_size_mb_by_variant():
    catalog = load_catalog()
    wiki = catalog["wikipedia"]
    assert item_size_mb(wiki, {"variant": "simple"}) == 1050
    assert item_size_mb(wiki, {"variant": "nopic"}) == 52700


def test_item_size_mb_by_option_lookup():
    catalog = load_catalog()
    gut = catalog["gutenberg"]
    # top_n=100 maps to 300 MB.
    assert item_size_mb(gut, {"top_n": 100}) == 300
    assert item_size_mb(gut, {"top_n": 2000}) == 6000


def test_item_size_mb_falls_back_to_default():
    catalog = load_catalog()
    gut = catalog["gutenberg"]
    # No opts given → defaults{top_n: 500} picks 1500 MB.
    assert item_size_mb(gut, {}) == 1500


def test_item_size_mb_unknown_returns_none():
    # Make a synthetic item with no size mapping.
    fake = {"id": "x", "defaults": {}}
    assert item_size_mb(fake, {}) is None


# ─────────────────────────────── save ────────────────────────────────────

def test_save_local_config_round_trip(tmp_path, monkeypatch):
    _redirect_config(monkeypatch, tmp_path)
    save_local_config("minimal", overrides={"wikipedia": {"variant": "nopic"}})
    loaded = load_yaml(tmp_path / "install.local.yaml")
    assert loaded["preset"] == "minimal"
    assert loaded["overrides"]["wikipedia"]["variant"] == "nopic"


# ─────────────────────────── setup diff logic ────────────────────────────

def test_diff_from_preset_adds():
    from rag.setup import diff_from_preset
    preset = {"wikipedia": {"variant": "simple"}}
    chosen = {"wikipedia": {"variant": "simple"}, "ifixit": {}}
    assert diff_from_preset(preset, chosen) == {"ifixit": {}}


def test_diff_from_preset_removes():
    from rag.setup import diff_from_preset
    preset = {"wikipedia": {"variant": "simple"}, "ifixit": {}}
    chosen = {"wikipedia": {"variant": "simple"}}
    # Removed items become None so load_effective_config drops them.
    assert diff_from_preset(preset, chosen) == {"ifixit": None}


def test_diff_from_preset_changes_option():
    from rag.setup import diff_from_preset
    preset = {"wikipedia": {"variant": "simple"}}
    chosen = {"wikipedia": {"variant": "nopic"}}
    assert diff_from_preset(preset, chosen) == {"wikipedia": {"variant": "nopic"}}


def test_diff_from_preset_identical_is_empty():
    from rag.setup import diff_from_preset
    preset = {"wikipedia": {"variant": "simple"}}
    assert diff_from_preset(preset, preset) == {}


# ─────────────────────────────── helpers ─────────────────────────────────

def _redirect_config(monkeypatch, tmp_path: Path):
    """Point install_config at a tmp_path config/ dir but keep catalog/presets."""
    # Copy the real catalog + presets so loading still resolves. Only redirect
    # install.yaml / install.local.yaml paths.
    real_catalog = install_config.CATALOG_PATH
    real_install = install_config.INSTALL_PATH
    real_local = install_config.INSTALL_LOCAL_PATH
    real_presets = install_config.PRESETS_DIR

    monkeypatch.setattr(install_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(install_config, "INSTALL_PATH", tmp_path / "install.yaml")
    monkeypatch.setattr(install_config, "INSTALL_LOCAL_PATH", tmp_path / "install.local.yaml")
    # Catalog + presets stay real.
    monkeypatch.setattr(install_config, "CATALOG_PATH", real_catalog)
    monkeypatch.setattr(install_config, "PRESETS_DIR", real_presets)


def _write(path: Path, data: dict):
    path.write_text(yaml.safe_dump(data, sort_keys=False))
