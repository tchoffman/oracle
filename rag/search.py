"""Semantic search over the Chroma index — no LLM in the loop.

Returns the top-K most similar chunks for a query. Useful when you want the
raw references instead of a synthesized answer, or when you don't trust the
LLM to pick well and want to look yourself.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from rag.config import load_config
from rag.query import _format_source, retrieve

console = Console()


def search(question: str, k: int | None = None) -> list[dict]:
    """Return raw retrieval hits with text + metadata + distance."""
    cfg = load_config()
    if k is not None:
        cfg = dict(cfg)
        cfg["retrieve_k"] = k
    return retrieve(cfg, question)


def _print_hits(question: str, hits: list[dict]) -> None:
    console.print(Rule(f"[bold]Search: {question}"))
    if not hits:
        console.print("[yellow]No corpus indexed — run `make index` or `make zim-index` first.[/yellow]")
        return
    for i, h in enumerate(hits, 1):
        label = _format_source(h["meta"])
        dist = h.get("dist")
        score = f"dist={dist:.3f}" if dist is not None else ""
        preview = h["text"].strip().replace("\n", " ")[:400]
        if len(h["text"]) > 400:
            preview += " …"
        console.print(Panel(preview, title=f"[{i}] {label}  [dim]{score}[/dim]", border_style="cyan"))


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: pergamon search \"your query\" [--k N]", file=sys.stderr)
        return 2
    k = None
    parts: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--k" and i + 1 < len(argv):
            k = int(argv[i + 1]); i += 2
        else:
            parts.append(argv[i]); i += 1
    query = " ".join(parts).strip()
    if not query:
        print("Usage: pergamon search \"your query\" [--k N]", file=sys.stderr)
        return 2
    hits = search(query, k=k)
    _print_hits(query, hits)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
