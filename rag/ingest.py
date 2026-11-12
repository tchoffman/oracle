"""Ingest PDFs under build/corpus/pdfs/ into a persistent Chroma collection.

Idempotent: re-running skips chunks whose (source_path, chunk_index) is already present.
Embeddings are computed via Ollama's embed endpoint.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Iterator

import chromadb
import ollama
from pypdf import PdfReader
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from rag.config import REPO_ROOT, load_config

console = Console()


def chunk_text(text: str, size: int, overlap: int) -> Iterator[str]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    i = 0
    n = len(text)
    while i < n:
        end = min(i + size, n)
        chunk = text[i:end].strip()
        if chunk:
            yield chunk
        if end == n:
            break
        i = end - overlap


def extract_pdf(path: Path) -> str:
    """Join all page text into a single string."""
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        console.print(f"[yellow]skip[/yellow] {path.name}: cannot read PDF ({e})")
        return ""
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            # malformed page — skip silently; many PDFs have a few of these
            continue
    return "\n".join(pages)


def chunk_id(source: str, idx: int) -> str:
    h = hashlib.sha1(f"{source}:{idx}".encode()).hexdigest()[:16]
    return f"{Path(source).stem}-{idx:04d}-{h}"


def embed(client: ollama.Client, model: str, text: str) -> list[float]:
    resp = client.embeddings(model=model, prompt=text)
    return resp["embedding"]


def main() -> int:
    cfg = load_config()
    pdf_dir = REPO_ROOT / "build" / "corpus" / "pdfs"
    if not pdf_dir.exists():
        console.print(f"[red]No corpus at {pdf_dir}. Run `make corpus` first.[/red]")
        return 1

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        console.print(f"[yellow]No PDFs found under {pdf_dir}. Nothing to index.[/yellow]")
        return 0

    console.print(f"Found [bold]{len(pdfs)}[/bold] PDF(s) under {pdf_dir}")

    client_chroma = chromadb.PersistentClient(path=cfg["chroma_dir"])
    coll = client_chroma.get_or_create_collection(cfg["chroma_collection"])
    existing_ids = set(coll.get(include=[])["ids"])
    console.print(f"Chroma collection [bold]{cfg['chroma_collection']}[/bold] has {len(existing_ids)} chunks already.")

    client_ollama = ollama.Client(host=cfg["ollama_host"])

    total_added = 0
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        for pdf in pdfs:
            text = extract_pdf(pdf)
            if not text.strip():
                console.print(f"[yellow]skip[/yellow] {pdf.name}: no extractable text")
                continue
            chunks = list(chunk_text(text, cfg["chunk_size"], cfg["chunk_overlap"]))
            task = progress.add_task(f"[cyan]{pdf.name}", total=len(chunks))
            batch_ids: list[str] = []
            batch_docs: list[str] = []
            batch_embs: list[list[float]] = []
            batch_meta: list[dict] = []
            for idx, chunk in enumerate(chunks):
                cid = chunk_id(pdf.name, idx)
                if cid in existing_ids:
                    progress.advance(task)
                    continue
                emb = embed(client_ollama, cfg["embedding_model"], chunk)
                batch_ids.append(cid)
                batch_docs.append(chunk)
                batch_embs.append(emb)
                batch_meta.append({"source": pdf.name, "chunk_index": idx})
                progress.advance(task)
                if len(batch_ids) >= 64:
                    coll.add(ids=batch_ids, documents=batch_docs, embeddings=batch_embs, metadatas=batch_meta)
                    total_added += len(batch_ids)
                    batch_ids, batch_docs, batch_embs, batch_meta = [], [], [], []
            if batch_ids:
                coll.add(ids=batch_ids, documents=batch_docs, embeddings=batch_embs, metadatas=batch_meta)
                total_added += len(batch_ids)

    console.print(f"[green]Added {total_added} new chunks.[/green] Collection total: {coll.count()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
