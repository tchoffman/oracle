"""Ingest ZIM articles into the Chroma collection.

Reads each article, strips HTML, chunks, embeds, and stores with metadata that
lets `pergamon ask` link back to the kiwix-serve URL for the source.

Idempotent — deterministic chunk IDs mean re-runs skip already-ingested content.

Honors env vars:
    ZIM_LIMIT   — max number of articles to ingest per ZIM (default: unlimited)
    ZIM_SKIP    — skip entries whose title doesn't contain any of these (comma-sep)
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import chromadb
import ollama
from bs4 import BeautifulSoup
from libzim.reader import Archive
from rich.console import Console
from rich.progress import (
    BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn,
)

from rag.config import REPO_ROOT, load_config
from rag.ingest import chunk_text

console = Console()


def extract_article_text(html_bytes: bytes) -> str:
    """Strip HTML to plain text. Drops script/style and most nav chrome."""
    soup = BeautifulSoup(html_bytes, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # Try to pull the main content area first (works for kiwix's Wikipedia).
    main = soup.find("main") or soup.find(id="mw-content-text") or soup.find("body") or soup
    return main.get_text(" ", strip=True)


def chunk_id(zim_name: str, entry_path: str, idx: int) -> str:
    key = f"{zim_name}::{entry_path}::{idx}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]


def embed(client: ollama.Client, model: str, text: str) -> list[float]:
    return client.embeddings(model=model, prompt=text)["embedding"]


def ingest_zim(
    zim_path: Path,
    coll: chromadb.Collection,
    cfg: dict,
    ollama_client: ollama.Client,
    limit: int | None = None,
    batch_size: int = 32,
) -> int:
    """Ingest one ZIM. Returns number of new chunks added."""
    archive = Archive(str(zim_path))
    zim_name = zim_path.name

    # Pre-fetch existing IDs for this ZIM to skip already-ingested articles quickly.
    existing_prefix: set[str] = set()
    try:
        existing = coll.get(where={"source": zim_name}, include=[])
        existing_prefix = set(existing.get("ids", []))
    except Exception:
        pass

    article_total = archive.article_count
    console.print(
        f"[cyan]{zim_name}[/cyan]: {article_total} articles; "
        f"{len(existing_prefix)} chunks already indexed"
    )

    n_added = 0
    n_articles = 0
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_embs: list[list[float]] = []
    batch_meta: list[dict] = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"{zim_name}", total=(limit or article_total))
        for entry in archive.iter_efficient():
            if entry.is_redirect:
                continue
            item = entry.get_item()
            if "html" not in item.mimetype:
                continue

            text = extract_article_text(bytes(item.content))
            if len(text) < 200:  # skip tiny stubs / disambig pages
                continue

            chunks = list(chunk_text(text, cfg["chunk_size"], cfg["chunk_overlap"]))
            for idx, chunk in enumerate(chunks):
                cid = chunk_id(zim_name, entry.path, idx)
                if cid in existing_prefix:
                    continue
                batch_ids.append(cid)
                batch_docs.append(chunk)
                batch_meta.append({
                    "source": zim_name,
                    "zim_path": entry.path,
                    "title": entry.title,
                    "chunk_index": idx,
                })
                if len(batch_ids) >= batch_size:
                    _flush(coll, ollama_client, cfg, batch_ids, batch_docs, batch_meta)
                    n_added += len(batch_ids)
                    existing_prefix.update(batch_ids)
                    batch_ids, batch_docs, batch_embs, batch_meta = [], [], [], []

            n_articles += 1
            progress.update(task, completed=n_articles)
            if limit and n_articles >= limit:
                break

        if batch_ids:
            _flush(coll, ollama_client, cfg, batch_ids, batch_docs, batch_meta)
            n_added += len(batch_ids)

    console.print(
        f"[green]{zim_name}[/green]: processed {n_articles} articles, added {n_added} new chunks"
    )
    return n_added


def _flush(
    coll: chromadb.Collection,
    client: ollama.Client,
    cfg: dict,
    ids: list[str],
    docs: list[str],
    meta: list[dict],
):
    embs = [embed(client, cfg["embedding_model"], d) for d in docs]
    coll.add(ids=ids, documents=docs, embeddings=embs, metadatas=meta)


def main(argv: list[str]) -> int:
    if not argv:
        console.print(
            "Usage: python -m rag.zim_ingest <zim-path> [<zim-path> ...]\n"
            "Env: ZIM_LIMIT=N to cap articles per ZIM.",
            style="red",
        )
        return 2

    cfg = load_config()
    limit_env = os.environ.get("ZIM_LIMIT")
    limit = int(limit_env) if limit_env else None

    client_chroma = chromadb.PersistentClient(path=cfg["chroma_dir"])
    coll = client_chroma.get_or_create_collection(cfg["chroma_collection"])

    client_ollama = ollama.Client(host=cfg["ollama_host"])

    total = 0
    for arg in argv:
        p = Path(arg)
        if not p.exists():
            console.print(f"[red]skip:[/red] {p} does not exist")
            continue
        total += ingest_zim(p, coll, cfg, client_ollama, limit=limit)

    console.print(
        f"[bold green]Done.[/bold green] Added {total} new chunks across {len(argv)} ZIM(s). "
        f"Collection now has {coll.count()} chunks."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
