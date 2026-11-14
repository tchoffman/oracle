"""Lightweight web UI for Pergamon.

Run with:
    bin/pergamon web                 # :8090
    bin/pergamon web --port 9000     # custom port

Single-page UI (Jinja2 + HTMX, no SPA framework). SSE streams the RAG answer
token-by-token. Links out to kiwix-serve for ZIM browse.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import chromadb
import ollama
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from rag.config import REPO_ROOT, load_config
from rag.query import SYSTEM_PROMPT, _format_source, build_context, retrieve

TEMPLATES_DIR = REPO_ROOT / "rag" / "templates"
STATIC_DIR = REPO_ROOT / "rag" / "static"

app = FastAPI(title="Pergamon", docs_url=None, redoc_url=None)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_cfg = load_config()


def _zim_list() -> list[dict]:
    """ZIMs available for browse (links go to the kiwix-serve process)."""
    zim_dir = REPO_ROOT / "build" / "corpus" / "zims"
    if not zim_dir.exists():
        return []
    out = []
    for z in sorted(zim_dir.glob("*.zim")):
        stem = z.stem
        out.append({"name": z.name, "stem": stem, "size_mb": z.stat().st_size // (1024 * 1024)})
    return out


def _status() -> dict:
    """Light status pulled from the current state."""
    cfg = load_config()
    try:
        c = chromadb.PersistentClient(path=cfg["chroma_dir"])
        chunks = c.get_or_create_collection(cfg["chroma_collection"]).count()
    except Exception:
        chunks = -1
    zims = _zim_list()
    return {
        "chunks": chunks,
        "zims": len(zims),
        "model": cfg["llm_model"],
        "embedding_model": cfg["embedding_model"],
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "status": _status(),
            "zims": _zim_list(),
            "kiwix_available": shutil.which("kiwix-serve") is not None
            or (REPO_ROOT / "build" / "bin" / "kiwix-serve").exists()
            or Path("/Applications/Kiwix.app").exists(),
        },
    )


@app.get("/status")
def status():
    return _status()


@app.get("/ask")
async def ask(q: str):
    """Server-Sent Events stream of a RAG answer.

    Event types:
      source  — a citation (sent once per retrieved chunk, before tokens)
      token   — one streamed LLM token
      done    — terminal event
    """
    cfg = load_config()
    hits = retrieve(cfg, q)

    async def event_gen():
        # Emit sources first so the client can render citations while tokens stream.
        if hits:
            for i, h in enumerate(hits, 1):
                label = _format_source(h["meta"])
                yield {"event": "source", "data": f"[{i}] {label}"}
            context, _ = build_context(hits, cfg["max_context_chars"])
            user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {q}"
        else:
            yield {"event": "source", "data": "(no corpus — answering from general knowledge)"}
            user_prompt = f"QUESTION: {q}"

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
        # ollama's stream is a sync generator — yield to the event loop between tokens.
        for chunk in stream:
            piece = chunk["message"]["content"]
            if piece:
                yield {"event": "token", "data": piece}
            await asyncio.sleep(0)

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_gen())
