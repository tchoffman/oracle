"""Generic record-keeping primitive.

A "ledger" is a typed collection of records backed by SQLite. Each ledger is
defined declaratively in `config/ledgers/<name>.yaml`:

    name: food
    title: Food Inventory
    fields:
      - {name: item, type: text, required: true}
      - {name: qty, type: number}
      - {name: unit, type: text}
      - {name: location, type: enum, options: [pantry, freezer, fridge, cellar]}
      - {name: expires, type: date}
      - {name: notes, type: text}

Many future features (food inventory, seed library, maintenance log, journal,
medical records) are just configs on top of this engine.

Data lives at `build/ledger/<name>.db` — one SQLite file per ledger, gitignored.
Rows have a primary key `id` and `created`/`updated` timestamps auto-managed.

CLI (see `pergamon ledger`):
    pergamon ledger list                  List available ledgers
    pergamon ledger show <name>           Print all rows in a table
    pergamon ledger add <name> k=v ...    Insert a row
    pergamon ledger rm <name> <id>        Delete a row
    pergamon ledger query <name> <filt>   Filter: k=v  k~substr  k<N  k>N
"""
from __future__ import annotations

import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from rag.config import REPO_ROOT

console = Console()

LEDGERS_DIR = REPO_ROOT / "config" / "ledgers"
DB_DIR = REPO_ROOT / "build" / "ledger"

ALLOWED_TYPES = {"text", "number", "integer", "date", "enum", "bool"}
_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")


def _load_schema(name: str) -> dict:
    path = LEDGERS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no ledger schema: {path}")
    with open(path) as f:
        s = yaml.safe_load(f) or {}
    if s.get("name") != name:
        raise ValueError(f"schema {path} declares name={s.get('name')!r}, expected {name!r}")
    for f_ in s.get("fields") or []:
        fname = f_.get("name") or ""
        ftype = f_.get("type")
        if not _IDENT.fullmatch(fname):
            raise ValueError(f"invalid field name {fname!r} (must be lowercase snake_case)")
        if ftype not in ALLOWED_TYPES:
            raise ValueError(f"field {fname!r}: unknown type {ftype!r}")
    return s


def list_ledgers() -> list[str]:
    if not LEDGERS_DIR.exists():
        return []
    return sorted(p.stem for p in LEDGERS_DIR.glob("*.yaml"))


def _db_path(name: str) -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_DIR / f"{name}.db"


def _open_db(schema: dict) -> sqlite3.Connection:
    """Open the SQLite file and ensure the table exists with the schema's columns."""
    conn = sqlite3.connect(_db_path(schema["name"]))
    conn.row_factory = sqlite3.Row

    # Build CREATE TABLE. SQLite is typeless; we map our types to affinities
    # and enforce constraints at write time in Python.
    type_map = {
        "text": "TEXT",
        "number": "REAL",
        "integer": "INTEGER",
        "date": "TEXT",
        "enum": "TEXT",
        "bool": "INTEGER",
    }
    cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for f in schema["fields"]:
        col = f"{f['name']} {type_map[f['type']]}"
        if f.get("required"):
            col += " NOT NULL"
        cols.append(col)
    cols.append("created TEXT NOT NULL")
    cols.append("updated TEXT NOT NULL")
    conn.execute(f"CREATE TABLE IF NOT EXISTS {schema['name']} ({', '.join(cols)})")

    # Idempotent column add — allows evolving the schema over time.
    existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({schema['name']})")}
    for f in schema["fields"]:
        if f["name"] not in existing:
            conn.execute(
                f"ALTER TABLE {schema['name']} ADD COLUMN {f['name']} {type_map[f['type']]}"
            )
    conn.commit()
    return conn


def _coerce(field: dict, raw: str):
    """Convert a CLI string to a Python value matching the field's type."""
    t = field["type"]
    if raw is None or raw == "":
        return None
    if t == "text" or t == "enum":
        if t == "enum" and raw not in (field.get("options") or []):
            raise ValueError(
                f"{field['name']}={raw!r} not in enum options {field.get('options')}"
            )
        return raw
    if t == "number":
        return float(raw)
    if t == "integer":
        return int(raw)
    if t == "bool":
        return 1 if raw.lower() in ("1", "true", "yes", "y", "on") else 0
    if t == "date":
        # Accept ISO or YYYY-MM-DD; normalize to YYYY-MM-DD.
        return datetime.fromisoformat(raw).date().isoformat()
    raise ValueError(f"unknown type {t}")


def _parse_kv(args: list[str]) -> dict:
    """k=v pairs from CLI. Quote values with spaces at the shell level."""
    out = {}
    for a in args:
        if "=" not in a:
            raise ValueError(f"expected key=value, got {a!r}")
        k, v = a.split("=", 1)
        out[k] = v
    return out


def add_row(name: str, values: dict) -> int:
    schema = _load_schema(name)
    conn = _open_db(schema)
    field_map = {f["name"]: f for f in schema["fields"]}
    # Validate required fields are present + coerce types.
    row: dict = {}
    for k, v in values.items():
        if k not in field_map:
            raise ValueError(f"unknown field {k!r} in ledger {name!r}")
        row[k] = _coerce(field_map[k], v)
    for f in schema["fields"]:
        if f.get("required") and row.get(f["name"]) is None:
            raise ValueError(f"missing required field {f['name']!r}")
    now = datetime.now().isoformat(timespec="seconds")
    row["created"] = now
    row["updated"] = now
    cols = ",".join(row.keys())
    placeholders = ",".join("?" * len(row))
    cur = conn.execute(
        f"INSERT INTO {name} ({cols}) VALUES ({placeholders})",
        list(row.values()),
    )
    conn.commit()
    return cur.lastrowid


def remove_row(name: str, row_id: int) -> bool:
    schema = _load_schema(name)
    conn = _open_db(schema)
    cur = conn.execute(f"DELETE FROM {name} WHERE id = ?", (row_id,))
    conn.commit()
    return cur.rowcount > 0


def _parse_filter(f: str) -> tuple[str, str, str]:
    """Parse a single filter token: k=v, k~sub, k<N, k>N. Returns (col, op, val)."""
    for sep in ("<=", ">=", "~", "=", "<", ">"):
        if sep in f:
            col, val = f.split(sep, 1)
            return col, sep, val
    raise ValueError(f"bad filter: {f}")


def query_rows(name: str, filters: list[str] | None = None) -> list[dict]:
    schema = _load_schema(name)
    conn = _open_db(schema)
    valid_cols = {f["name"] for f in schema["fields"]} | {"id", "created", "updated"}

    where_parts: list[str] = []
    params: list = []
    for f in filters or []:
        col, op, val = _parse_filter(f)
        if col not in valid_cols:
            raise ValueError(f"unknown column {col!r}")
        if op == "~":
            where_parts.append(f"{col} LIKE ?")
            params.append(f"%{val}%")
        else:
            sql_op = {"=": "=", "<": "<", ">": ">", "<=": "<=", ">=": ">="}[op]
            where_parts.append(f"{col} {sql_op} ?")
            params.append(val)

    sql = f"SELECT * FROM {name}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += " ORDER BY id"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def show(name: str, filters: list[str] | None = None) -> None:
    schema = _load_schema(name)
    rows = query_rows(name, filters)
    cols = ["id"] + [f["name"] for f in schema["fields"]] + ["updated"]
    table = Table(title=schema.get("title", name))
    for c in cols:
        table.add_column(c)
    for r in rows:
        table.add_row(*[str(r.get(c) or "") for c in cols])
    console.print(table)
    console.print(f"[dim]{len(rows)} row(s) · {_db_path(name)}[/dim]")


def _print_available() -> None:
    names = list_ledgers()
    if not names:
        console.print(
            "[yellow]No ledgers defined.[/yellow] Add a YAML to config/ledgers/."
        )
        return
    table = Table(title="Ledgers")
    table.add_column("name")
    table.add_column("title")
    table.add_column("fields")
    for n in names:
        try:
            s = _load_schema(n)
            table.add_row(n, s.get("title", ""), ", ".join(f["name"] for f in s["fields"]))
        except Exception as e:
            table.add_row(n, f"[red]{e}[/red]", "")
    console.print(table)


# ─────────────────────────────── CLI ────────────────────────────────────

def main(argv: list[str]) -> int:
    if not argv or argv[0] == "list":
        _print_available()
        return 0

    cmd = argv[0]

    if cmd == "show" and len(argv) >= 2:
        show(argv[1], argv[2:])
        return 0

    if cmd == "add" and len(argv) >= 3:
        name = argv[1]
        try:
            values = _parse_kv(argv[2:])
            rid = add_row(name, values)
            console.print(f"[green]added[/green] {name}#{rid}")
        except Exception as e:
            console.print(f"[red]error:[/red] {e}")
            return 1
        return 0

    if cmd == "rm" and len(argv) == 3:
        name, row_id = argv[1], int(argv[2])
        if remove_row(name, row_id):
            console.print(f"[green]removed[/green] {name}#{row_id}")
            return 0
        console.print(f"[yellow]no row {row_id} in {name}[/yellow]")
        return 1

    if cmd == "query" and len(argv) >= 2:
        show(argv[1], argv[2:])
        return 0

    console.print(
        "Usage:\n"
        "  pergamon ledger list\n"
        "  pergamon ledger show <name> [filter ...]\n"
        "  pergamon ledger add <name> field=value [...]\n"
        "  pergamon ledger rm <name> <id>\n"
        "  pergamon ledger query <name> field=value [field~sub ...]"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
