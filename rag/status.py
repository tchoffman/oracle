"""Print oracle readiness: deps, models, corpus, index."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

from rag.config import REPO_ROOT, load_config

console = Console()


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def dir_size_mb(p: Path) -> int:
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total // (1024 * 1024)


def ollama_models(host: str) -> list[str]:
    try:
        import ollama
        c = ollama.Client(host=host)
        resp = c.list()
        return [m.get("name") or m.get("model") for m in resp.get("models", [])]
    except Exception:
        return []


def chroma_count(cfg: dict) -> int:
    try:
        import chromadb
        c = chromadb.PersistentClient(path=cfg["chroma_dir"])
        coll = c.get_or_create_collection(cfg["chroma_collection"])
        return coll.count()
    except Exception:
        return -1


def main() -> int:
    cfg = load_config()
    table = Table(title="Oracle status", show_lines=False)
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    table.add_row("ollama binary", "[green]installed[/green]" if have("ollama") else "[red]missing[/red]")

    local_kiwix = REPO_ROOT / "build" / "bin" / "kiwix-serve"
    if local_kiwix.exists():
        table.add_row("kiwix-serve", f"[green]headless binary[/green] ({local_kiwix})")
    elif have("kiwix-serve"):
        table.add_row("kiwix-serve", "[green]headless binary[/green] (on PATH)")
    elif Path("/Applications/Kiwix.app").exists():
        table.add_row("kiwix-serve", "[yellow]GUI only[/yellow] (Kiwix.app — oracle serve will launch it)")
    else:
        table.add_row("kiwix-serve", "[red]missing[/red]")

    models = ollama_models(cfg["ollama_host"])
    if models:
        table.add_row("ollama models", ", ".join(models))
    else:
        table.add_row("ollama models", "[yellow]none (server down or no models)[/yellow]")

    zim_dir = REPO_ROOT / "build" / "corpus" / "zims"
    pdf_dir = REPO_ROOT / "build" / "corpus" / "pdfs"
    zims = list(zim_dir.glob("*.zim")) if zim_dir.exists() else []
    pdfs = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    table.add_row("ZIMs", f"{len(zims)} file(s), {dir_size_mb(zim_dir)} MB")
    table.add_row("PDFs", f"{len(pdfs)} file(s), {dir_size_mb(pdf_dir)} MB")

    count = chroma_count(cfg)
    if count < 0:
        table.add_row("Chroma index", "[yellow]not yet built[/yellow]")
    else:
        table.add_row("Chroma index", f"{count} chunks")

    console.print(table)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
