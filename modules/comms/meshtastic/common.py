"""Shared helpers: running a RAG query, chunking the answer for LoRa.

Keeps the mesh-facing code identical in mock and real modes.
"""
from __future__ import annotations

from dataclasses import dataclass

import ollama

from rag.config import load_config
from rag.query import SYSTEM_PROMPT, _format_source, build_context, retrieve

# Meshtastic messages cap around 240 bytes of payload. Leave headroom for
# UTF-8 multi-byte chars and our "[p/N] " prefix.
MAX_MESH_CHARS = 200


@dataclass
class MeshReply:
    answer: str
    sources: list[str]

    def chunks(self, max_chars: int = MAX_MESH_CHARS) -> list[str]:
        """Split the full reply (answer + top source) into LoRa-sized chunks.

        Each chunk is prefixed with [p/N] so receivers can reassemble out of
        order. Prefers splitting on whitespace boundaries.
        """
        body = self.answer.strip()
        if self.sources:
            body += "\n\n" + self.sources[0]

        pieces: list[str] = []
        remaining = body
        while remaining:
            if len(remaining) <= max_chars:
                pieces.append(remaining)
                break
            # Try to split on a word boundary near max_chars.
            split_at = remaining.rfind(" ", 0, max_chars)
            if split_at < max_chars // 2:
                split_at = max_chars  # fall back to hard split
            pieces.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()

        n = len(pieces)
        return [f"[{i + 1}/{n}] {p}" for i, p in enumerate(pieces)]


def ask(question: str, max_tokens_hint: int = 150) -> MeshReply:
    """Run the RAG pipeline synchronously and return a MeshReply.

    Deliberately short answers: mesh users don't want essays. The system
    prompt gets an extra hint to stay terse.
    """
    cfg = load_config()
    hits = retrieve(cfg, question)

    if hits:
        context, sources = build_context(hits, cfg["max_context_chars"])
        user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    else:
        sources = []
        user_prompt = f"QUESTION: {question}"

    short_hint = (
        "\n\nRespond in at most 2 sentences. This reply will be relayed over "
        "low-bandwidth mesh radio; brevity is a safety feature."
    )
    client = ollama.Client(host=cfg["ollama_host"])
    resp = client.chat(
        model=cfg["llm_model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + short_hint},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": cfg["temperature"], "num_ctx": cfg["num_ctx"]},
    )
    answer = resp["message"]["content"].strip()

    # Trim to just the top source for brevity; include only the article title.
    short_sources: list[str] = []
    if hits:
        top = _format_source(hits[0]["meta"])
        # Keep the human-readable part only, drop the long kiwix URL.
        short_sources = [top.split("  (")[0] if "  (" in top else top]

    return MeshReply(answer=answer, sources=short_sources)
