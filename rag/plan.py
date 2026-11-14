"""Planning: RAG + a planner-tuned system prompt.

Takes a goal, retrieves relevant context (same as `ask`), but nudges the LLM
into a structured plan rather than a Q&A answer.
"""
from __future__ import annotations

import sys

import ollama
from rich.console import Console
from rich.rule import Rule

from rag.config import load_config
from rag.query import build_context, retrieve

console = Console()


PLAN_SYSTEM_PROMPT = """You are Pergamon's planner. The user describes a goal; you
produce a practical, grounded plan.

Structure the plan EXACTLY like this (markdown):

**Goal**: one-sentence restatement

**Steps**
1. ...
2. ...
(numbered, each one line, in execution order)

**Resources needed**
- materials, tools, references, time estimate

**Risks & mitigations**
- what could go wrong → how to handle it

**Verification**
- how you'll know it worked

Rules:
- Use CONTEXT where relevant and cite sources inline like [1], [2].
- Be concrete: numbers, specific gear, specific steps. No hedging.
- Off-grid / wilderness / survival planning assumes limited internet,
  limited tools, and the user handling things alone or in a small group.
- For medical, legal, or dangerous subjects, name the obvious caveats
  without burying the plan."""


def make_plan(goal: str, stream: bool = True) -> int:
    cfg = load_config()
    hits = retrieve(cfg, goal)

    if hits:
        context, sources = build_context(hits, cfg["max_context_chars"])
        user_prompt = f"CONTEXT:\n{context}\n\nGOAL: {goal}"
    else:
        context, sources = "", []
        user_prompt = (
            f"(No corpus indexed yet — planning from general knowledge alone.)\n\nGOAL: {goal}"
        )

    client = ollama.Client(host=cfg["ollama_host"])
    kwargs = dict(
        model=cfg["llm_model"],
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": cfg["temperature"], "num_ctx": cfg["num_ctx"]},
    )

    console.print(Rule("[bold green]Plan"))
    if stream:
        for chunk in client.chat(stream=True, **kwargs):
            piece = chunk["message"]["content"]
            if piece:
                console.out(piece, end="")
        console.print("")
    else:
        resp = client.chat(**kwargs)
        console.print(resp["message"]["content"])

    if sources:
        console.print(Rule("[bold]Sources"))
        for s in sources:
            console.print(f"  • {s}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pergamon plan \"your goal\"", file=sys.stderr)
        sys.exit(2)
    sys.exit(make_plan(" ".join(sys.argv[1:])))
