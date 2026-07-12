"""Tests for the persistent Nexus memory store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.memory import MemoryStore


def test_add_persists_and_loads_entry(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    added = store.add("User prefers concise answers", metadata={"role": "user"})

    loaded = MemoryStore(tmp_path)

    assert loaded.entries == (added,)
    assert loaded.entries[0].metadata == {"role": "user"}


def test_search_ranks_relevant_memories(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("The user has a black cat named Luna")
    store.add("The weather is sunny today")
    store.add("Luna the cat prefers tuna")

    results = store.search("What food does the cat Luna prefer?", limit=2)

    assert [result.entry.text for result in results] == [
        "Luna the cat prefers tuna",
        "The user has a black cat named Luna",
    ]
    assert results[0].score > results[1].score > 0


def test_search_returns_empty_for_no_match(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Remember the grocery list")

    assert store.search("astronomy") == []


def test_capacity_prunes_oldest_entries(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path, max_entries=2, max_age_days=None)
    store.add("first")
    store.add("second")
    store.add("third")

    assert [entry.text for entry in store.entries] == ["second", "third"]
    assert [entry.text for entry in MemoryStore(tmp_path).entries] == ["second", "third"]


def test_age_pruning_removes_stale_entries(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    store = MemoryStore(tmp_path, max_age_days=None)
    store.add("stale", created_at=now - timedelta(days=31), persist=False)
    store.add("current", created_at=now - timedelta(days=2), persist=False)
    store.max_age_days = 30

    assert store.prune(now=now) == 1
    assert [entry.text for entry in store.entries] == ["current"]


def test_json_file_path_is_configurable(tmp_path: Path) -> None:
    path = tmp_path / "custom-memory.json"
    store = MemoryStore(path)
    store.add("stored in a custom file")

    assert path.exists()
    assert MemoryStore(path).entries[0].text == "stored in a custom file"


def test_unsupported_format_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Only the 'json'"):
        MemoryStore(tmp_path, storage_format="sqlite")


def test_corrupt_storage_has_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot load memory store"):
        MemoryStore(path)
