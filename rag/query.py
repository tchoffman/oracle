"""Ask the library a question. Retrieves relevant chunks, synthesizes with the LLM."""
from __future__ import annotations

import sys

import chromadb
import ollama
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from rag.config import load_config

console = Console()


SYSTEM_PROMPT = """You are Pergamon, an offline library assistant for someone operating
off-grid without internet. Answer practically and concisely using ONLY the provided
CONTEXT when possible. If context doesn't cover the question, say so and offer your
best general knowledge, flagging it as such. For medical, legal, or dangerous subjects,
remind the user of the obvious limits of any text-based reference."""


def retrieve(cfg: dict, question: str) -> list[dict]:
    client_chroma = chromadb.PersistentClient(path=cfg["chroma_dir"])
    coll = client_chroma.get_or_create_collection(cfg["chroma_collection"])
    if coll.count() == 0:
        return []
    client_ollama = ollama.Client(host=cfg["ollama_host"])
    q_emb = client_ollama.embeddings(model=cfg["embedding_model"], prompt=question)["embedding"]
    res = coll.query(query_embeddings=[q_emb], n_results=cfg["retrieve_k"])
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    return [{"text": d, "meta": m, "dist": dist} for d, m, dist in zip(docs, metas, dists)]


def _format_source(meta: dict, kiwix_port: int = 8080) -> str:
    """Turn a chunk's metadata into a human-readable citation.

    ZIM-sourced chunks get a browse URL into kiwix-serve so the user can jump
    to the full article. PDF chunks fall back to source#chunk.
    """
    source = meta.get("source", "?")
    if "zim_path" in meta:
        title = meta.get("title", meta["zim_path"])
        zim_stem = source.rsplit(".", 1)[0]  # strip .zim
        url = f"http://localhost:{kiwix_port}/viewer#{zim_stem}/{meta['zim_path']}"
        return f"{source} — {title}  ({url})"
    return f"{source}#chunk{meta.get('chunk_index', '?')}"


def build_context(hits: list[dict], cap: int) -> tuple[str, list[str]]:
    sources: list[str] = []
    parts: list[str] = []
    used = 0
    for i, h in enumerate(hits, 1):
        label = f"[{i}] {_format_source(h['meta'])}"
        block = f"=== {label} ===\n{h['text'].strip()}\n"
        if used + len(block) > cap and parts:
            break
        parts.append(block)
        sources.append(label)
        used += len(block)
    return "\n".join(parts), sources


def ask(question: str) -> int:
    cfg = load_config()
    hits = retrieve(cfg, question)

    if hits:
        context, sources = build_context(hits, cfg["max_context_chars"])
        user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    else:
        context, sources = "", []
        user_prompt = (
            f"(No corpus indexed yet — answering from general knowledge.)\n\nQUESTION: {question}"
        )

    client_ollama = ollama.Client(host=cfg["ollama_host"])
    stream = client_ollama.chat(
        model=cfg["llm_model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        options={"temperature": cfg["temperature"], "num_ctx": cfg["num_ctx"]},
    )

    console.print(Rule("[bold green]Pergamon"))
    buf = []
    for chunk in stream:
        piece = chunk["message"]["content"]
        buf.append(piece)
        console.out(piece, end="")
    console.print("")
    if sources:
        console.print(Rule("[bold]Sources"))
        for s in sources:
            console.print(f"  • {s}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m rag.query 'your question here'", file=sys.stderr)
        sys.exit(2)
    sys.exit(ask(" ".join(sys.argv[1:])))
