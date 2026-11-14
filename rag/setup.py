"""Interactive setup TUI for Pergamon.

Walks the operator through a profile pick + optional per-item customization,
then writes config/install.local.yaml so the fetchers do the right thing on
the next `make corpus`.

Modules (comms, services) will plug in here later — see the MODULES list.
"""
from __future__ import annotations

import sys
from typing import Any

import questionary
from questionary import Choice
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from rag.install_config import (
    available_presets,
    item_size_mb,
    load_catalog,
    load_effective_config,
    load_model_catalog,
    load_yaml,
    save_local_config,
    PRESETS_DIR,
)

console = Console()


def _format_mb(mb: int | None) -> str:
    if mb is None:
        return "?"
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb} MB"


def _summary_table(catalog: dict, enable: dict) -> Table:
    tbl = Table(title="Planned install", show_lines=False)
    tbl.add_column("Item", style="cyan")
    tbl.add_column("Options")
    tbl.add_column("Size", justify="right")
    total = 0
    for item_id, opts in enable.items():
        item = catalog.get(item_id)
        if not item:
            tbl.add_row(f"[red]{item_id}[/red]", "unknown", "?")
            continue
        size = item_size_mb(item, opts or {})
        if size:
            total += size
        opts_str = ", ".join(f"{k}={v}" for k, v in (opts or {}).items()) or "-"
        tbl.add_row(item["title"], opts_str, _format_mb(size))
    tbl.caption = f"Approximate total: {_format_mb(total)}"
    return tbl


def _prompt_profile() -> str:
    """Ask for preset or custom build."""
    presets = available_presets()
    choices = [
        Choice(title=f"{p['name']:<15} — {p['description']}", value=p["file"])
        for p in presets
    ]
    choices.append(Choice(title="custom          — start from a preset, then edit each item", value="__custom__"))
    return questionary.select("Pick an install profile:", choices=choices).ask()


def _prompt_item_options(item: dict, current: dict | None) -> dict:
    """Interactively collect options for a single item."""
    out: dict[str, Any] = dict(current or {})
    for opt in item.get("options") or []:
        name = opt["name"]
        prompt = opt.get("prompt", name)
        default = out.get(name, item.get("defaults", {}).get(name))

        if "choices" in opt and opt.get("multi"):
            default_list = default if isinstance(default, list) else []
            answer = questionary.checkbox(
                prompt,
                choices=[
                    Choice(c["label"], value=c["value"], checked=(c["value"] in default_list))
                    for c in opt["choices"]
                ],
            ).ask()
            out[name] = answer or []
        elif "choices" in opt:
            answer = questionary.select(
                prompt,
                choices=[
                    Choice(c["label"], value=c["value"])
                    for c in opt["choices"]
                ],
                default=default,
            ).ask()
            if answer is not None:
                out[name] = answer
        elif opt.get("type") == "string":
            placeholder = opt.get("placeholder", "")
            answer = questionary.text(prompt, default=(",".join(default) if isinstance(default, list) else (default or ""))).ask()
            if "," in prompt or opt.get("multi"):
                out[name] = [x.strip() for x in (answer or "").split(",") if x.strip()]
            else:
                out[name] = answer
        # Items with no options still appear in enable map as {} — that's fine.
    return out


def _custom_flow(catalog: dict, starting_enable: dict) -> dict:
    """Let the user toggle every item and customize per-item options."""
    console.print(
        Panel(
            "Custom mode: for each shelf, pick what to include. "
            "The current preset is pre-selected — leave boxes alone to accept it.",
            title="Custom install",
            style="cyan",
        )
    )

    # Group items by shelf for a cleaner flow.
    by_shelf: dict[str, list[dict]] = {}
    for item in catalog.values():
        by_shelf.setdefault(item.get("shelf", "other"), []).append(item)

    chosen: dict[str, dict] = {}
    shelf_order = sorted(by_shelf.keys())
    for shelf in shelf_order:
        items = sorted(by_shelf[shelf], key=lambda x: x["title"])
        picks = questionary.checkbox(
            f"Shelf '{shelf}' — include which?",
            choices=[
                Choice(
                    title=f"{it['title']} — {it.get('description', '')}",
                    value=it["id"],
                    checked=(it["id"] in starting_enable),
                )
                for it in items
            ],
        ).ask() or []
        for pick in picks:
            item = catalog[pick]
            current_opts = starting_enable.get(pick) or {}
            chosen[pick] = _prompt_item_options(item, current_opts)
    return chosen


def _prompt_models(current: dict) -> dict:
    """Ask for primary + embedding model selection.

    `current` is the pre-selected models (preset defaults or existing local).
    Returns a dict like {"primary": "id", "embedding": "id"}.
    """
    model_cat = load_model_catalog()
    chosen: dict[str, str] = {}

    console.print(Rule("[bold]Models"))
    console.print(
        "Pick the primary LLM and the embedding model. Bigger models give better "
        "answers but need more RAM and run slower. [yellow]Changing the embedding "
        "model requires reindexing the whole corpus[/yellow] — vectors from one "
        "model aren't compatible with another."
    )

    for role in ("primary", "embedding"):
        role_label = "LLM (synthesis)" if role == "primary" else "Embedding (retrieval)"
        options = model_cat.get(role, {})
        if not options:
            continue

        def _label(m: dict) -> str:
            size = m.get("size_mb", 0)
            size_s = f"{size/1024:.1f} GB" if size >= 1024 else f"{size} MB"
            dim = f", {m['dim']}d" if "dim" in m else ""
            return f"{m['id']:<22} {size_s:>8}{dim}  — {m.get('notes', '')}"

        default = current.get(role)
        if default not in options:
            default = next(iter(options))
        choice = questionary.select(
            f"{role_label}:",
            choices=[Choice(_label(m), value=m_id) for m_id, m in options.items()],
            default=default,
        ).ask()
        if choice:
            chosen[role] = choice

    # Warn if embedding changed vs current.
    if current.get("embedding") and chosen.get("embedding") and chosen["embedding"] != current["embedding"]:
        console.print(
            "[yellow]Note:[/yellow] you've changed the embedding model. "
            "Run [cyan]rm -rf build/chroma && make index[/cyan] (and "
            "[cyan]make zim-index[/cyan] if you had ZIMs indexed) afterwards."
        )
    return chosen


def diff_from_preset(preset_enable: dict, chosen_enable: dict) -> dict:
    """Compute the minimal `overrides:` block that transforms preset_enable
    into chosen_enable. Removed items are mapped to None so the merge logic
    in install_config.load_effective_config can drop them.

    Pure function — safe to unit-test.
    """
    overrides: dict[str, Any] = {}
    for k, v in chosen_enable.items():
        if preset_enable.get(k) != v:
            overrides[k] = v
    for k in preset_enable:
        if k not in chosen_enable:
            overrides[k] = None
    return overrides


# Module hook: future modules (comms, services) register setup functions here.
# Each function takes (catalog, current_config_dict) and returns updated dict.
# For v0.1 only corpus flow exists; others are no-ops.
MODULES: list[tuple[str, callable]] = []


def main() -> int:
    catalog = load_catalog()

    # Load current effective config so toggles start in a sensible place.
    current = load_effective_config()
    starting_enable = current["enable"]
    console.print(Panel.fit(
        "[bold]Pergamon setup[/bold]\n\n"
        "This picks what gets installed when you run [cyan]make corpus[/cyan] / [cyan]make all[/cyan].\n"
        "Choices are written to [dim]config/install.local.yaml[/dim] (gitignored).",
        title="welcome", style="green",
    ))

    profile = _prompt_profile()
    if not profile:
        console.print("[yellow]Cancelled.[/yellow]")
        return 1

    if profile == "__custom__":
        base_preset_choice = questionary.select(
            "Start customizing from which preset?",
            choices=[Choice(p["name"], value=p["file"]) for p in available_presets()],
            default=current["preset"],
        ).ask()
        base = load_yaml(PRESETS_DIR / f"{base_preset_choice}.yaml")
        chosen_enable = _custom_flow(catalog, base.get("enable") or starting_enable)
    else:
        base = load_yaml(PRESETS_DIR / f"{profile}.yaml")
        chosen_enable = base.get("enable") or {}
        base_preset_choice = profile

    # Models — always offered, even for a plain preset pick.
    preset_models = base.get("models") or {}
    starting_models = {**preset_models, **(current.get("models") or {})}
    chosen_models = _prompt_models(starting_models)

    # Show summary and confirm.
    console.print(_summary_table(catalog, chosen_enable))
    if chosen_models:
        console.print(
            f"[dim]models:[/dim] primary=[cyan]{chosen_models.get('primary','?')}[/cyan] "
            f"embedding=[cyan]{chosen_models.get('embedding','?')}[/cyan]"
        )
    confirmed = questionary.confirm("Save this configuration?", default=True).ask()
    if not confirmed:
        console.print("[yellow]Aborted — no changes written.[/yellow]")
        return 1

    # Only persist model picks if they differ from the preset's defaults.
    model_overrides = {k: v for k, v in chosen_models.items() if preset_models.get(k) != v}

    # If we customized, write enable-overrides. Otherwise just point at the preset.
    if profile == "__custom__":
        preset_enable = load_yaml(PRESETS_DIR / f"{base_preset_choice}.yaml").get("enable") or {}
        overrides = diff_from_preset(preset_enable, chosen_enable)
        save_local_config(base_preset_choice, overrides=overrides, models=model_overrides)
    else:
        save_local_config(profile, models=model_overrides)

    console.print(f"[green]Saved to[/green] config/install.local.yaml")
    console.print("\nNext steps:")
    console.print("  [cyan]make corpus[/cyan]    # download selected items")
    console.print("  [cyan]make index[/cyan]     # embed any new PDFs")
    console.print("  [cyan]make status[/cyan]    # see what's ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
