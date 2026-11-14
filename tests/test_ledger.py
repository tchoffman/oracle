"""Unit tests for rag.ledger — pure logic, uses tmp_path for the SQLite file."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rag import ledger


def _seed_schema(tmp_dir: Path, name: str) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / f"{name}.yaml"
    path.write_text(yaml.safe_dump({
        "name": name,
        "title": "Test Ledger",
        "fields": [
            {"name": "item", "type": "text", "required": True},
            {"name": "qty", "type": "number"},
            {"name": "unit", "type": "text"},
            {"name": "location", "type": "enum", "options": ["pantry", "freezer"]},
            {"name": "expires", "type": "date"},
            {"name": "active", "type": "bool"},
            {"name": "notes", "type": "text"},
        ],
    }))
    return path


@pytest.fixture
def tmp_ledgers(tmp_path, monkeypatch):
    """Redirect LEDGERS_DIR and DB_DIR to tmp_path."""
    schemas = tmp_path / "schemas"
    dbs = tmp_path / "db"
    _seed_schema(schemas, "ptest")
    monkeypatch.setattr(ledger, "LEDGERS_DIR", schemas)
    monkeypatch.setattr(ledger, "DB_DIR", dbs)
    return {"schemas": schemas, "dbs": dbs}


def test_list_ledgers(tmp_ledgers):
    assert ledger.list_ledgers() == ["ptest"]


def test_add_and_show(tmp_ledgers):
    rid = ledger.add_row("ptest", {"item": "rice", "qty": "10", "unit": "lb"})
    assert rid == 1
    rows = ledger.query_rows("ptest")
    assert len(rows) == 1
    assert rows[0]["item"] == "rice"
    assert rows[0]["qty"] == 10.0  # coerced to float


def test_missing_required_field(tmp_ledgers):
    with pytest.raises(ValueError, match="missing required field"):
        ledger.add_row("ptest", {"qty": "5"})


def test_unknown_field(tmp_ledgers):
    with pytest.raises(ValueError, match="unknown field"):
        ledger.add_row("ptest", {"item": "x", "nonsense": "y"})


def test_enum_rejects_bad_value(tmp_ledgers):
    with pytest.raises(ValueError, match="not in enum options"):
        ledger.add_row("ptest", {"item": "x", "location": "garage"})


def test_date_coercion(tmp_ledgers):
    ledger.add_row("ptest", {"item": "x", "expires": "2027-01-15"})
    rows = ledger.query_rows("ptest")
    assert rows[0]["expires"] == "2027-01-15"


def test_bool_coercion(tmp_ledgers):
    ledger.add_row("ptest", {"item": "a", "active": "yes"})
    ledger.add_row("ptest", {"item": "b", "active": "false"})
    rows = ledger.query_rows("ptest")
    active = {r["item"]: r["active"] for r in rows}
    assert active["a"] == 1
    assert active["b"] == 0


def test_query_equality(tmp_ledgers):
    ledger.add_row("ptest", {"item": "rice", "location": "pantry"})
    ledger.add_row("ptest", {"item": "beef", "location": "freezer"})
    hits = ledger.query_rows("ptest", ["location=pantry"])
    assert [h["item"] for h in hits] == ["rice"]


def test_query_substring(tmp_ledgers):
    ledger.add_row("ptest", {"item": "brown rice"})
    ledger.add_row("ptest", {"item": "white rice"})
    ledger.add_row("ptest", {"item": "quinoa"})
    hits = ledger.query_rows("ptest", ["item~rice"])
    assert len(hits) == 2


def test_query_range(tmp_ledgers):
    ledger.add_row("ptest", {"item": "a", "qty": "1"})
    ledger.add_row("ptest", {"item": "b", "qty": "5"})
    ledger.add_row("ptest", {"item": "c", "qty": "10"})
    hits = ledger.query_rows("ptest", ["qty>3", "qty<9"])
    assert [h["item"] for h in hits] == ["b"]


def test_remove_row(tmp_ledgers):
    rid = ledger.add_row("ptest", {"item": "x"})
    assert ledger.remove_row("ptest", rid) is True
    assert ledger.query_rows("ptest") == []
    assert ledger.remove_row("ptest", rid) is False


def test_invalid_schema_name_rejected(tmp_ledgers):
    # Schema must be defined before you can touch it.
    with pytest.raises(FileNotFoundError):
        ledger.add_row("nonexistent", {"item": "x"})


def test_food_schema_in_real_catalog():
    """The committed food.yaml parses and has sensible fields."""
    from rag.config import REPO_ROOT
    path = REPO_ROOT / "config" / "ledgers" / "food.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert data["name"] == "food"
    field_names = {f["name"] for f in data["fields"]}
    assert "item" in field_names
    assert "expires" in field_names
