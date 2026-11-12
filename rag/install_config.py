"""Load the merged install config and the catalog.

The *effective* config is:
    preset (config/presets/<name>.yaml)
        <- merged with config/install.yaml.overrides
        <- merged with config/install.local.yaml.overrides

Fetchers consume the effective config.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rag.config import REPO_ROOT

CONFIG_DIR = REPO_ROOT / "config"
CATALOG_PATH = CONFIG_DIR / "catalog.yaml"
INSTALL_PATH = CONFIG_DIR / "install.yaml"
INSTALL_LOCAL_PATH = CONFIG_DIR / "install.local.yaml"
PRESETS_DIR = CONFIG_DIR / "presets"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_catalog() -> dict:
    """Return catalog.yaml as dict keyed by item id."""
    raw = load_yaml(CATALOG_PATH)
    items = {item["id"]: item for item in raw.get("items", [])}
    return items


def _merge_enable(preset_enable: dict, overrides: dict) -> dict:
    """Merge override map onto preset's enable map. None value removes."""
    merged = {k: dict(v) if isinstance(v, dict) else v for k, v in preset_enable.items()}
    for key, val in (overrides or {}).items():
        if val is None:
            merged.pop(key, None)
        elif isinstance(val, dict):
            cur = merged.get(key) or {}
            merged[key] = {**cur, **val}
        else:
            merged[key] = val
    return merged


def load_effective_config() -> dict:
    """Return the effective install config: {"enable": {item_id: options, ...}}."""
    install = load_yaml(INSTALL_PATH)
    local = load_yaml(INSTALL_LOCAL_PATH) if INSTALL_LOCAL_PATH.exists() else {}

    # Prefer local.preset if given, else install.preset.
    preset_name = local.get("preset") or install.get("preset") or "default"
    preset = load_yaml(PRESETS_DIR / f"{preset_name}.yaml")

    enable = preset.get("enable") or {}
    enable = _merge_enable(enable, install.get("overrides") or {})
    enable = _merge_enable(enable, local.get("overrides") or {})

    return {"preset": preset_name, "enable": enable}


def save_local_config(preset_name: str, overrides: dict | None = None) -> None:
    """Write config/install.local.yaml."""
    data = {"preset": preset_name}
    if overrides:
        data["overrides"] = overrides
    with open(INSTALL_LOCAL_PATH, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def item_size_mb(item: dict, opts: dict) -> int | None:
    """Best-effort size estimate for an item given its chosen options."""
    if "size_mb_by_variant" in item:
        v = (opts or {}).get("variant") or item.get("defaults", {}).get("variant") or "default"
        return item["size_mb_by_variant"].get(v)
    if "size_mb_by_option" in item:
        key, mapping = next(iter(item["size_mb_by_option"].items()))
        val = (opts or {}).get(key) or item.get("defaults", {}).get(key)
        return mapping.get(val)
    return None


def available_presets() -> list[dict]:
    """List presets with name/description."""
    out = []
    if PRESETS_DIR.exists():
        for p in sorted(PRESETS_DIR.glob("*.yaml")):
            d = load_yaml(p)
            out.append({"file": p.stem, "name": d.get("name", p.stem), "description": d.get("description", "")})
    return out
