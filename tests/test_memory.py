"""Tests for the structured Nexus memory system."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.memory import (
    DEFAULT_RETENTION,
    ContradictionRecord,
    MemoryEntry,
    MemoryManager,
    MemoryResult,
    MemoryScope,
    MemorySource,
    MemoryStore,
    MemorySummary,
    MemoryType,
    RetentionPolicy,
    SensitivityLevel,
)
from src.memory.retrieval import MemoryRetriever, RetrievalQuery


def test_add_with_all_fields(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    entry = store.add(
        "User likes Estonian coffee",
        memory_type=MemoryType.PREFERENCE,
        source=MemorySource.USER_STATED,
        confidence=0.9,
        importance=0.8,
        sensitivity=SensitivityLevel.LOW,
        scope=MemoryScope.GLOBAL,
    )
    assert entry.memory_type == MemoryType.PREFERENCE
    assert entry.source == MemorySource.USER_STATED
    assert entry.confidence == 0.9
    assert entry.importance == 0.8
    assert entry.sensitivity == SensitivityLevel.LOW
    assert entry.scope == MemoryScope.GLOBAL
    assert entry.id in [e.id for e in store.entries]


def test_legacy_memory_migrates_safely(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.json"
    legacy_payload = {
        "version": 1,
        "entries": [
            {
                "id": "legacy-1",
                "text": "Old style memory",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"role": "user"},
            }
        ],
    }
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    store = MemoryStore(legacy_path)
    assert len(store.entries) == 1
    entry = store.entries[0]
    assert entry.text == "Old style memory"
    assert entry.memory_type == MemoryType.EPISODIC
    assert entry.source == MemorySource.USER_STATED
    assert entry.scope == MemoryScope.GLOBAL


def test_new_format_persists_as_version_two(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add(
        "New format memory",
        memory_type=MemoryType.SEMANTIC,
        source=MemorySource.ASSISTANT_INFERRED,
        confidence=0.8,
        importance=0.7,
        sensitivity=SensitivityLevel.MEDIUM,
        scope=MemoryScope.PROJECT,
    )
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    first = raw["entries"][0]
    assert first["memory_type"] == "semantic"
    assert first["source"] == "assistant_inferred"
    assert first["sensitivity"] == "medium"
    assert first["scope"] == "project"


def test_memory_type_enum_values() -> None:
    assert MemoryType.WORKING.value == "working"
    assert MemoryType.EPISODIC.value == "episodic"
    assert MemoryType.SEMANTIC.value == "semantic"
    assert MemoryType.PREFERENCE.value == "preference"
    assert MemoryType.PROCEDURAL.value == "procedural"


def test_search_with_type_filter(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Prefers dark mode", memory_type=MemoryType.PREFERENCE)
    store.add("Had a meeting yesterday", memory_type=MemoryType.EPISODIC)
    store.add("Python uses indentation", memory_type=MemoryType.SEMANTIC)
    manager = MemoryManager(store)
    results = manager.retrieve(RetrievalQuery("prefers dark mode", types=(MemoryType.PREFERENCE,)))
    assert len(results) == 1
    assert results[0].entry.memory_type == MemoryType.PREFERENCE


def test_promote_working_to_long_term(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    working = manager.add_working_memory("Temporary thought about coffee")
    assert working.memory_type == MemoryType.WORKING
    promoted = manager.promote_to_long_term(working.id)
    assert promoted is not None
    assert promoted.memory_type == MemoryType.EPISODIC


def test_consolidate_duplicates(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    manager.add_working_memory("User likes cats", metadata={"topic": "pets"})
    manager.add_working_memory("user likes cats", metadata={"topic": "pets"})
    survivors = manager.consolidate_duplicates()
    texts = [s.text for s in survivors]
    assert len(survivors) == 1
    assert len(store.entries) == 1


def test_contradiction_handling(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    manager = MemoryManager(store)
    existing = store.add(
        "User prefers tea",
        memory_type=MemoryType.PREFERENCE,
        confidence=0.3,
        importance=0.4,
    )
    incoming = store.add(
        "User prefers coffee",
        memory_type=MemoryType.PREFERENCE,
        confidence=0.9,
        importance=0.8,
    )
    record = manager.handle_contradiction(existing, incoming)
    assert record is not None
    assert record.resolution == "supersede"


def test_apply_retention_policy(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path, max_age_days=None)
    manager = MemoryManager(store)
    now = datetime.now(timezone.utc)
    store.add("Old entry", created_at=now - timedelta(days=200), persist=False)
    store.add("New entry", persist=False)
    removed = manager.apply_retention(RetentionPolicy(max_age_days=90))
    assert removed == 1
    assert len(store.entries) == 1
    assert store.entries[0].text == "New entry"


def test_apply_retention_max_entries_pruning(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path, max_age_days=None)
    manager = MemoryManager(store)
    for i in range(5):
        store.add(f"Entry {i}", importance=float(5 - i) / 5.0, persist=False)
    removed = manager.apply_retention(RetentionPolicy(max_age_days=None, max_entries=3))
    assert removed == 2
    assert len(store.entries) == 3


def test_legacy_sensitivity_invalid_falls_back_to_low(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.json"
    legacy_payload = {
        "version": 1,
        "entries": [
            {
                "id": "legacy-1",
                "text": "Old style memory",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"sensitivity": "totally_invalid"},
            }
        ],
    }
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    store = MemoryStore(legacy_path)
    assert store.entries[0].sensitivity == SensitivityLevel.LOW


def test_retriever_keyword_only(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Python is a programming language", memory_type=MemoryType.SEMANTIC)
    store.add("Cats are furry animals", memory_type=MemoryType.SEMANTIC)
    retriever = MemoryRetriever(store.entries)
    results = retriever.search(RetrievalQuery("programming language", limit=2))
    assert len(results) == 1
    assert "programming" in results[0].entry.text.lower()
    assert results[0].retrieval_path == "keyword"


def test_retriever_hybrid(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("Python is a programming language", memory_type=MemoryType.SEMANTIC)
    store.add("Cats are furry animals", memory_type=MemoryType.SEMANTIC)

    def fake_embed(text: str) -> tuple[float, ...]:
        lowered = text.lower()
        return (1.0, 0.0) if "python" in lowered or "programming" in lowered else (0.0, 1.0)

    retriever = MemoryRetriever(store.entries, embedding_fn=fake_embed)
    results = retriever.search(RetrievalQuery("programming language", limit=2))
    assert len(results) == 1
    assert "python" in results[0].entry.text.lower()
    assert results[0].retrieval_path == "hybrid"


def test_retriever_token_budget(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("One two three", memory_type=MemoryType.EPISODIC)
    store.add("Four five six seven eight nine", memory_type=MemoryType.EPISODIC)
    retriever = MemoryRetriever(store.entries)
    results = retriever.search(RetrievalQuery("numbers", limit=10, token_budget=4))
    assert len(results) <= 2


def test_migrate_legacy_counts(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.add("legacy-like entry")
    migrated = store.migrate()
    assert migrated == 1


def test_invalid_confidence_rejected(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    with pytest.raises(ValueError, match="confidence"):
        store.add("test", confidence=1.5)
    with pytest.raises(ValueError, match="importance"):
        store.add("test", importance=-0.1)


def test_add_and_search_backward_compatible(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    added = store.add("User prefers concise answers", metadata={"role": "user"})
    loaded = MemoryStore(tmp_path)
    assert loaded.entries == (added,)
    results = loaded.search("concise answers", limit=1)
    assert len(results) == 1
    assert results[0].entry.text == "User prefers concise answers"


def test_default_retention_policies_exist() -> None:
    assert MemoryType.WORKING in DEFAULT_RETENTION
    assert MemoryType.EPISODIC in DEFAULT_RETENTION
    assert MemoryType.SEMANTIC in DEFAULT_RETENTION
    assert MemoryType.PREFERENCE in DEFAULT_RETENTION
    assert MemoryType.PROCEDURAL in DEFAULT_RETENTION
